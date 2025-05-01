# app/services/job_scraper.py
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
from datetime import datetime, timedelta
from app.models.job import Job
from app import db
import logging

logger = logging.getLogger(__name__)

class JobScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def _setup_selenium(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"user-agent={self.headers['User-Agent']}")
        driver = webdriver.Chrome(options=chrome_options)
        return driver

    def _process_date_string(self, date_str):
        today = datetime.now()

        if 'today' in date_str.lower() or 'just now' in date_str.lower():
            return today.strftime('%Y-%m-%d')
        elif 'yesterday' in date_str.lower():
            return (today - timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'days ago' in date_str.lower():
            days = int(re.search(r'(\d+)', date_str).group(1))
            return (today - timedelta(days=days)).strftime('%Y-%m-%d')
        elif 'week' in date_str.lower():
            weeks = int(re.search(r'(\d+)', date_str).group(1)) if re.search(r'(\d+)', date_str) else 1
            return (today - timedelta(days=weeks*7)).strftime('%Y-%m-%d')
        elif 'month' in date_str.lower():
            months = int(re.search(r'(\d+)', date_str).group(1)) if re.search(r'(\d+)', date_str) else 1
            return (today - timedelta(days=months*30)).strftime('%Y-%m-%d')
        else:
            try:
                # Try to parse various date formats
                date_formats = [
                    '%b %d, %Y',
                    '%d %b %Y',
                    '%Y-%m-%d',
                    '%d/%m/%Y',
                    '%m/%d/%Y'
                ]

                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        return parsed_date.strftime('%Y-%m-%d')
                    except ValueError:
                        continue

                # If no format matches, return today's date
                return today.strftime('%Y-%m-%d')
            except Exception:
                return today.strftime('%Y-%m-%d')

    def scrape_linkedin(self, keywords, location=None, job_type=None, max_pages=3):
        driver = self._setup_selenium()
        jobs = []

        try:
            base_url = "https://www.linkedin.com/jobs/search/"
            query_params = f"?keywords={keywords.replace(' ', '%20')}"

            if location:
                query_params += f"&location={location.replace(' ', '%20')}"

            if job_type:
                # Map job_type to LinkedIn's filter values
                job_type_map = {
                    "full_time": "F",
                    "part_time": "P",
                    "contract": "C",
                    "internship": "I",
                    "remote": "R"
                }
                if job_type.lower() in job_type_map:
                    query_params += f"&f_JT={job_type_map[job_type.lower()]}"

            url = base_url + query_params
            driver.get(url)

            # Wait for job listings to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "jobs-search__results-list"))
            )

            for page in range(max_pages):
                # Scroll to load more jobs
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

                soup = BeautifulSoup(driver.page_source, 'html.parser')
                job_listings = soup.select('.jobs-search__results-list li')

                for job in job_listings:
                    try:
                        job_link_elem = job.select_one('a.job-card-container__link')
                        job_title = job_link_elem.text.strip() if job_link_elem else "No title"
                        job_url = job_link_elem['href'] if job_link_elem else "#"

                        company_elem = job.select_one('.job-card-container__company-name')
                        company = company_elem.text.strip() if company_elem else "No company"

                        location_elem = job.select_one('.job-card-container__metadata-item')
                        job_location = location_elem.text.strip() if location_elem else "No location"

                        date_elem = job.select_one('.job-card-container__listed-time')
                        post_date_text = date_elem.text.strip() if date_elem else "No date"
                        post_date = self._process_date_string(post_date_text)

                        # Check if job mode contains remote
                        job_mode = "Remote" if "remote" in job_location.lower() else "Onsite"

                        jobs.append({
                            'title': job_title,
                            'company': company,
                            'location': job_location,
                            'job_mode': job_mode,
                            'job_type': job_type if job_type else "Not specified",
                            'post_date': post_date,
                            'url': job_url,
                            'source': 'LinkedIn',
                            'description': "",  # Need to click on job to get description
                            'salary': "Not specified"
                        })

                    except Exception as e:
                        logger.error(f"Error scraping LinkedIn job: {e}")
                        continue

                # Try to click on "Next" button if it exists
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, ".artdeco-pagination__button--next")
                    if "artdeco-button--disabled" not in next_button.get_attribute("class"):
                        next_button.click()
                        time.sleep(3)
                    else:
                        break
                except Exception:
                    break

        except Exception as e:
            logger.error(f"Error in LinkedIn scraping: {e}")

        finally:
            driver.quit()

        return jobs

    def scrape_indeed(self, keywords, location=None, job_type=None, max_pages=3):
        jobs = []

        try:
            base_url = "https://www.indeed.com/jobs"
            query_params = f"?q={keywords.replace(' ', '+')}"

            if location:
                query_params += f"&l={location.replace(' ', '+')}"

            if job_type:
                job_type_map = {
                    "full_time": "fulltime",
                    "part_time": "parttime",
                    "contract": "contract",
                    "internship": "internship",
                    "remote": "remote"
                }
                if job_type.lower() in job_type_map:
                    query_params += f"&jt={job_type_map[job_type.lower()]}"

            for page in range(max_pages):
                url = base_url + query_params + f"&start={page * 10}"
                response = requests.get(url, headers=self.headers)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    job_cards = soup.select('.job_seen_beacon')

                    if not job_cards:
                        # Try alternative selectors if structure changes
                        job_cards = soup.select('.jobsearch-ResultsList > li')

                    if not job_cards:
                        break

                    for job in job_cards:
                        try:
                            # Try to extract job details with multiple selectors for robustness
                            title_elem = job.select_one('h2.jobTitle a') or job.select_one('.jobTitle')
                            title = title_elem.text.strip() if title_elem else "No title"

                            company_elem = job.select_one('span.companyName') or job.select_one('.company_location .companyName')
                            company = company_elem.text.strip() if company_elem else "No company"

                            location_elem = job.select_one('div.companyLocation') or job.select_one('.company_location .companyLocation')
                            location = location_elem.text.strip() if location_elem else "No location"

                            # Check if job is remote
                            job_mode = "Remote" if "remote" in location.lower() else "Onsite"

                            date_elem = job.select_one('span.date') or job.select_one('.date')
                            post_date_text = date_elem.text.strip() if date_elem else "No date"
                            post_date = self._process_date_string(post_date_text)

                            # Try to get job URL
                            job_url = "https://www.indeed.com" + (title_elem.get('href') if title_elem and title_elem.get('href') else "")

                            # Try to get salary
                            salary_elem = job.select_one('.salary-snippet') or job.select_one('.salaryText')
                            salary = salary_elem.text.strip() if salary_elem else "Not specified"

                            jobs.append({
                                'title': title,
                                'company': company,
                                'location': location,
                                'job_mode': job_mode,
                                'job_type': job_type if job_type else "Not specified",
                                'post_date': post_date,
                                'url': job_url,
                                'source': 'Indeed',
                                'description': "",  # Needs separate call to job page
                                'salary': salary
                            })

                        except Exception as e:
                            logger.error(f"Error scraping Indeed job: {e}")
                            continue
                else:
                    logger.error(f"Failed to fetch Indeed page: {response.status_code}")
                    break

        except Exception as e:
            logger.error(f"Error in Indeed scraping: {e}")

        return jobs

    def scrape_internshala(self, keywords, location=None, job_type=None, max_pages=3):
        driver = self._setup_selenium()
        jobs = []

        try:
            base_url = "https://internshala.com/internships"
            query_params = f"/keywords-{keywords.replace(' ', '%20')}"

            if location:
                query_params += f"/location-{location.replace(' ', '%20')}"

            url = base_url + query_params
            driver.get(url)

            # Wait for job listings to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "internship_meta"))
            )

            for page in range(max_pages):
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                job_listings = soup.select('.individual_internship')

                for job in job_listings:
                    try:
                        title_elem = job.select_one('.profile')
                        title = title_elem.text.strip() if title_elem else "No title"

                        company_elem = job.select_one('.company_name')
                        company = company_elem.text.strip() if company_elem else "No company"

                        location_elem = job.select_one('.location_link')
                        job_location = location_elem.text.strip() if location_elem else "No location"

                        # Check if work from home is mentioned
                        work_from_home = job.select_one('.wfh_false')
                        job_mode = "Remote" if work_from_home and "work from home" in work_from_home.text.lower() else "Onsite"

                        # Get job details including stipend
                        stipend_elem = job.select_one('.stipend')
                        stipend = stipend_elem.text.strip() if stipend_elem else "Not specified"

                        # Get job link
                        link_elem = job.select_one('a.view_detail_button')
                        job_url = "https://internshala.com" + link_elem['href'] if link_elem and 'href' in link_elem.attrs else ""

                        # Get duration
                        duration_elem = job.select_one('.internship_other_details_container .other_detail_item > .item_body')
                        duration = duration_elem.text.strip() if duration_elem else "Not specified"

                        # Assume posting date is recent for internshala
                        post_date = datetime.now().strftime('%Y-%m-%d')

                        jobs.append({
                            'title': title,
                            'company': company,
                            'location': job_location,
                            'job_mode': job_mode,
                            'job_type': "Internship",
                            'duration': duration,
                            'post_date': post_date,
                            'url': job_url,
                            'source': 'Internshala',
                            'description': "",  # Needs separate call to job page
                            'salary': stipend
                        })

                    except Exception as e:
                        logger.error(f"Error scraping Internshala job: {e}")
                        continue

                # Try to go to next page if available
                try:
                    next_button = driver.find_element(By.LINK_TEXT, "Next")
                    if next_button.is_displayed() and next_button.is_enabled():
                        next_button.click()
                        time.sleep(2)
                    else:
                        break
                except Exception:
                    break

        except Exception as e:
            logger.error(f"Error in Internshala scraping: {e}")

        finally:
            driver.quit()

        return jobs

    def save_jobs_to_db(self, jobs):
        """Save scraped jobs to database"""
        saved_count = 0

        for job_data in jobs:
            # Check if job already exists (by URL or by title + company combination)
            existing_job = Job.query.filter(
                (Job.url == job_data['url']) |
                ((Job.title == job_data['title']) & (Job.company == job_data['company']))
            ).first()

            if not existing_job:
                job = Job(
                    title=job_data['title'],
                    company=job_data['company'],
                    location=job_data['location'],
                    job_mode=job_data['job_mode'],
                    job_type=job_data['job_type'],
                    post_date=job_data['post_date'],
                    url=job_data['url'],
                    source=job_data['source'],
                    description=job_data.get('description', ''),
                    salary=job_data.get('salary', 'Not specified')
                )

                db.session.add(job)
                saved_count += 1

        try:
            db.session.commit()
            return saved_count
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving jobs to database: {e}")
            return 0

    def scrape_all_sources(self, keywords, location=None, job_type=None, max_pages=2):
        """Scrape jobs from all sources and save to DB"""
        all_jobs = []

        # LinkedIn
        linkedin_jobs = self.scrape_linkedin(keywords, location, job_type, max_pages)
        all_jobs.extend(linkedin_jobs)

        # Indeed
        indeed_jobs = self.scrape_indeed(keywords, location, job_type, max_pages)
        all_jobs.extend(indeed_jobs)

        # Internshala
        internshala_jobs = self.scrape_internshala(keywords, location, job_type, max_pages)
        all_jobs.extend(internshala_jobs)

        # Save all jobs to DB
        saved_count = self.save_jobs_to_db(all_jobs)

        return {
            'total_jobs': len(all_jobs),
            'linkedin_jobs': len(linkedin_jobs),
            'indeed_jobs': len(indeed_jobs),
            'internshala_jobs': len(internshala_jobs),
            'new_jobs_saved': saved_count
        }