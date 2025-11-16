from scripts.preprocessing import ocr_extract_txt, legacy_extract_txt
from scripts.scraper import scrape_lulist
from scripts.postprocessing import clean_lu_df
from datetime import datetime
import os
import pandas as pd

lu_dir = "./lu_lists/new_lists"
temp_file_path = "./LockUpScraper2.0/output/temp/temp_lu.txt"
dir_list = os.listdir(lu_dir)
result_df = pd.DataFrame()

for i, file in enumerate(dir_list):
    full_path = os.path.join(lu_dir, file)

    if file.lower().endswith(('.pdf')):

        print(f"Processing: {file} ({i+1} of {len(dir_list)})")

        lu_text = legacy_extract_txt(full_path, temp_file_path)

        active_df = scrape_lulist(lu_text, quiet=True, print_errors=True)

        active_df['file_name'] = file
        active_df['entry_method'] = 'scraper_2.0'
        active_df['entry_date'] = datetime.today()
        
        result_df = pd.concat([result_df, active_df], ignore_index=True)

cleaned_df = clean_lu_df(result_df)

cleaned_df.to_csv('./LockUpScraper2.0/output/scraped_lulist.csv', index=False)
