# -*- coding: utf-8 -*-
"""
Created on Mon Apr  6 10:47:22 2026
tennis win probability from tennis abstract ELO
@author: uttam
"""
import cloudscraper
import pandas as pd
from bs4 import BeautifulSoup
import re

#%% functions
def extract_elo_data():
    url = "https://tennisabstract.com/reports/atp_elo_ratings.html"
    scraper = cloudscraper.create_scraper()
    html = scraper.get(url).text
    
    tables = pd.read_html(html)
    df = tables[2]
    return df

def extract_tournament_draw(tournament):
    url = "https://www.tennisabstract.com/current/2026ATPMonte-Carlo.html"
    scraper = cloudscraper.create_scraper()
    response = scraper.get(url)
    
    if response.status_code != 200: return "Failed to fetch page."

    # 1. Find the script tag containing 'var proj64'
    # check for each unique round in the tournament
    pattern = re.compile(r"var proj64\s*=\s*'(.*?)';", re.DOTALL)
    match = pattern.search(response.text)
    
    if not match: return "Could not find the 'proj64' variable in the page source."

    table_html = match.group(1)
    soup = BeautifulSoup(table_html, 'html.parser')
    
    data = []
    rows = soup.find_all('tr')
    
    for row in rows:
        cells = row.find_all(['td', 'th'])
        # Clean up the text (removing &nbsp; and extra spaces)
        row_data = [cell.get_text(strip=True).replace('\xa0', ' ') for cell in cells]
        if row_data:  data.append(row_data)

    if data:
        header_length = len(data[0])
        cleaned_data = [row for row in data if len(row) == header_length]
        
        header = cleaned_data[0]
        cleaned_data = [header] + [
            row for row in cleaned_data[1:] 
            if len(row) == len(header) and row != header
        ]
        
        df = pd.DataFrame(cleaned_data[1:], columns=cleaned_data[0])
        try: df = df.drop(columns=[''])
        except KeyError: df
        
        clist = df.columns.to_list()
        for c in clist:
            if(c != 'Player'): df[c] = df[c].str.rstrip('%').astype('float') / 100.0
            
        df['Player'] = df['Player'].str.replace(r'\(.*?\)','',regex=True)
        df['Player'] = df['Player'].str.strip()
        return df
    else:
        return "No data found in the variable string."

def elo_to_win(ra,rb):
    win_a = 1/(1+pow(10,(rb-ra)/400))
    win_b = 1/(1+pow(10,(ra-rb)/400))
    return win_a, win_b

def p_to_pts(df,level):
    if(level == '1000'): df['xPts'] = 1000*df['W'] + 650*(df['F']-df['W']) + 400*(df['SF']-df['F']) + 200*(df['QF']-df['SF']) + 100*(df['R16']-df['QF']) + 50*(df['R32']-df['R16']) + 10*(1-df['R32'])
    return df
    
#%% extract data
data = extract_tournament_draw('')
data = p_to_pts(data,'1000')