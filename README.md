# Leveraging Artificial Intelligence for Petroleum Well Data Extraction and Analysis
# Overview
This project is part of my master's dissertation, focusing on the application of Artificial Intelligence (AI) in the field of Geology, specifically in the extraction and analysis of petroleum well data. The Agência Nacional do Petróleo (ANP) in Brazil holds a vast repository of petroleum well data, which companies are legally required to submit. However, a significant challenge exists: many companies have not provided the original files that generated the composite profile charts found in these standardized PDFs. These original files are crucial for accurate analysis, yet they are only available for approximately 3% of the data in DLIS binary format, primarily from Petrobras.

# Problem Statement
Brazil's petroleum industry encompasses 16 basins, each containing at least a thousand wells, many of which are now deactivated. Geologists face the daunting task of manually transcribing values from these composite profile charts into their analysis software, a time-consuming and error-prone process. The lack of original data files exacerbates this issue, leading to inefficiencies in data analysis and decision-making.

# Project Objective
This project aims to assist geologists by developing a web scraper that automates the download of all necessary composite profile PDFs and their corresponding DLIS files from the ANP website. Using AI techniques, the project will then extract the data from these files and compare it against the verified 3% to ensure accuracy. The goal is to scale this extraction process to the entire dataset available at ANP, enabling more efficient and accurate geological analysis.

# Methodology
- Web Scraping: Automate the extraction of composite profile PDFs and DLIS files from the ANP website.
- Data Extraction with AI: Utilize AI models to extract relevant data from the downloaded files.
- Validation: Compare the extracted data with the 3% of known accurate DLIS files to validate the AI models.
- Scalability: Apply the validated extraction process to the entire ANP dataset.
# Expected Outcomes
- Enhanced Data Availability: Streamline the process of data extraction for geologists, reducing the need for manual transcription.
- Improved Accuracy: Ensure the extracted data is accurate and reliable through AI validation.
- Scalable Solution: Provide a scalable tool that can be used for ongoing and future geological data analysis.
# Repository Structure
/src - Contains all the code for web scraping and AI-based data extraction.  
/data - Sample data files used during development and testing.  
/notebooks - Jupyter notebooks used for exploratory data analysis and model development.  
/docs - Documentation and detailed explanations of the project.  
