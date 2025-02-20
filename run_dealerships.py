import os
import csv
import time
import logging
from typing import List, Tuple

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('neosemo_processing.log'),
        logging.StreamHandler()
    ]
)

# Optional AI processing (if API key is available)
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

class NeosemoAuditProcessor:
    def __init__(self, openai_api_key: str = None):
        """
        Initialize Neosemo Audit Processor
        
        :param openai_api_key: Optional OpenAI API key for AI assistance
        """
        self.driver = None
        self.ai_assistant = None
        
        # Try to set up AI if key is provided and libraries are available
        if AI_AVAILABLE and openai_api_key:
            try:
                self.setup_ai_assistant(openai_api_key)
            except Exception as e:
                logging.warning(f"Could not set up AI assistant: {e}")
                self.ai_assistant = None
    
    def setup_ai_assistant(self, openai_api_key: str):
        """
        Set up AI assistant if possible
        
        :param openai_api_key: OpenAI API key
        """
        llm = ChatOpenAI(
            model="gpt-3.5-turbo", 
            temperature=0.7, 
            api_key=openai_api_key
        )
        
        # Prompt template for URL analysis
        url_analysis_prompt = ChatPromptTemplate.from_template(
            """You are an expert in analyzing dealership websites. 
            Given a dealership URL: {url}
            Provide a brief, professional assessment of what you can infer about the dealership:
            - Likely type of dealership (brand, multi-brand, etc.)
            - Potential location or region
            - Any notable observations from the URL
            
            Be concise but insightful."""
        )
        
        # Create analysis chain
        self.analyze_url_chain = (
            url_analysis_prompt 
            | llm 
            | StrOutputParser()
        )
    
    def analyze_url(self, url: str) -> str:
        """
        Analyze a single URL using AI if available
        
        :param url: Dealership website URL
        :return: Insights about the URL
        """
        if self.ai_assistant and hasattr(self, 'analyze_url_chain'):
            try:
                return self.analyze_url_chain.invoke({"url": url})
            except Exception as e:
                logging.warning(f"AI analysis failed for {url}: {e}")
        return "No AI insights available"
    
    def setup_driver(self):
        """Set up and return a Chrome WebDriver instance."""
        chrome_options = Options()
        # Optional: Add headless mode if you want the browser to run in background
        # chrome_options.add_argument("--headless")
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
    
    def process_url(self, url: str) -> Tuple[str, str]:
        """
        Process a single URL on the Neosemo.ai website
        
        :param url: Dealership URL to process
        :return: Tuple of (original URL, audit report URL)
        """
        try:
            # AI-powered URL analysis (if available)
            url_insights = self.analyze_url(url)
            logging.info(f"URL Insights for {url}:\n{url_insights}")
            
            # Selenium processing
            self.driver.get("https://neosemo.ai/")
            time.sleep(2)
            
            # Fill URL
            try:
                url_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
                )
                url_input.clear()
                url_input.send_keys(url)
                logging.info(f"URL entered: {url}")
            except (TimeoutException, NoSuchElementException) as e:
                logging.error(f"Failed to enter URL {url}: {e}")
                return url, ''
            
            # Submit URL
            try:
                submit_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
                )
                submit_button.click()
                logging.info("URL submitted")
            except (TimeoutException, NoSuchElementException) as e:
                logging.error(f"Failed to submit URL {url}: {e}")
                return url, ''
            
            # Handle email
            try:
                email_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input#email"))
                )
                email_input.send_keys("JOSH@PROJECTXLABS.AI")
                logging.info("Email entered")
            except (TimeoutException, NoSuchElementException) as e:
                logging.error(f"Failed to enter email for {url}: {e}")
                return url, ''
            
            # Final submit
            try:
                final_submit = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='Submit']"))
                )
                final_submit.click()
                logging.info("Form submitted")
            except (TimeoutException, NoSuchElementException) as e:
                logging.error(f"Failed to submit form for {url}: {e}")
                return url, ''
            
            # Handle popup
            time.sleep(5)
            try:
                popup_close = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//*[@id='cta_178493']/div/div[2]"))
                )
                popup_close.click()
                logging.info("Popup closed")
            except (TimeoutException, NoSuchElementException):
                logging.info("No popup detected")
            
            # Get current URL (audit report URL)
            audit_report_url = self.driver.current_url
            logging.info(f"Audit Report URL: {audit_report_url}")
            return url, audit_report_url
        
        except Exception as e:
            logging.error(f"Unexpected error processing {url}: {e}")
            return url, ''
    
    def process_urls(self, input_file: str, output_file: str):
        """
        Process URLs from input CSV and generate audit reports
        
        :param input_file: Path to input CSV with URLs
        :param output_file: Path to output CSV with audit report URLs
        """
        # Setup WebDriver
        self.setup_driver()
        
        try:
            # Read URLs from input CSV
            with open(input_file, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                urls = [row[0] for row in reader]
            
            # Prepare output data
            output_data = []
            successful = []
            failed = []
            
            # Process each URL
            for url in urls:
                result_url, audit_report_url = self.process_url(url)
                
                if audit_report_url:
                    output_data.append([result_url, audit_report_url])
                    successful.append(result_url)
                else:
                    output_data.append([result_url, ''])
                    failed.append(result_url)
                
                time.sleep(2)  # Pause between processing
            
            # Write results to output CSV
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(output_data)
            
            # Print and log summary
            summary_message = f"""
--- Processing Complete ---
Successfully processed: {len(successful)} URLs
Failed to process: {len(failed)} URLs
"""
            logging.info(summary_message)
            print(summary_message)
            
            if failed:
                logging.info("Failed URLs:")
                for url in failed:
                    logging.info(f"- {url}")
        
        finally:
            # Always ensure driver is closed
            if self.driver:
                self.driver.quit()

def main():
    # Get OpenAI API key from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    input_file = 'dealer_urls.csv'
    output_file = 'dealer_urls_with_reports.csv'
    
    # Get API key, pass None if not set
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    # Create processor with optional API key
    processor = NeosemoAuditProcessor(openai_api_key)
    processor.process_urls(input_file, output_file)

if __name__ == "__main__":
    main()