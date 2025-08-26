
from slide.scrappers import Scrapper


class LogScrapper(Scrapper):
    def __init__(self, log_file_path):
        self.log_file_path = log_file_path

    def scrape(self):
        with open(self.log_file_path, 'r') as file:
            logs = file.readlines()
        return logs