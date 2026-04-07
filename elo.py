# -*- coding: utf-8 -*-
"""
Created on Mon Apr  6 10:47:22 2026
tennis win probability from tennis abstract ELO
@author: uttam
"""
import numpy as np
import pandas as pd
import cloudscraper
from bs4 import BeautifulSoup
import re
import random
from math import ceil, log2
from datetime import datetime

surface = 'c' # c, g, h
entrants = 56
seeds = 16

#%% functions
def extract_elo_data(use_scrapper):
    if(use_scrapper == 1):
        url = "https://tennisabstract.com/reports/atp_elo_ratings.html"
        scraper = cloudscraper.create_scraper()
        html = scraper.get(url).text
        
        tables = pd.read_html(html)
        df = tables[2]
    else:
        df =  pd.read_excel('C:/Users/Subramanya.Ganti/Downloads/Sports/tennis/copy.xlsx','Sheet1')
        
    df.columns = df.columns.str.replace('\xa0', ' ')
    df['Player'] = df['Player'].replace('old_value', 'new_value')
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
    
def randomize_seeds(l):
    g0 = l[0:1]
    g1 = l[1:2]
    g2 = l[2:4]; random.shuffle(g2)
    g3 = l[4:8]; random.shuffle(g3)
    g4 = l[8:16]; random.shuffle(g4)
    g5 = l[16:32]; random.shuffle(g5)
    
    new_l = g0 + g1 + g2 + g3 + g4 + g5
    return new_l
    
def generate_tennis_draw(n_players, m_seeds):
    SEED_TEMPLATES = {
        (128, 32): [1, 128, 33, 96, 17, 112, 49, 80, 9, 120, 41, 88, 25, 104, 57, 72, 
                    5, 124, 37, 92, 21, 108, 53, 76, 13, 116, 45, 84, 29, 100, 61, 68],
        (128, 16): [1, 128, 33, 96, 17, 112, 49, 80, 9, 120, 41, 88, 25, 104, 57, 72],
        (64, 16): [1, 64, 17, 48, 9, 56, 25, 40,  5, 60, 21, 44, 13, 52, 29, 36],
        (64, 8): [1, 64, 17, 48, 9, 56, 25, 40],
        (32, 8): [1, 32, 9, 24, 5, 28, 13, 20],
        (16, 4): [1, 16, 5, 12],
        (8, 4): [1, 8, 5, 4],
    }
    
    BYE_TEMPLATES = {
        (56, 16): [2, 63, 18, 47, 10, 55, 26, 39],
        (96, 32): [2, 127, 34, 95, 18, 111, 50, 79, 10, 119, 42, 87, 26, 103, 58, 71, 
                    6, 123, 38, 91, 22, 107, 54, 75, 14, 115, 46, 83, 30, 99, 62, 67],
        (48, 8): [2, 63, 18, 47, 10, 55, 26, 39]
    }

    
    if(m_seeds > n_players):  raise ValueError("Seeds exceed number of players")

    bracket_size = 2 ** ceil(log2(n_players))
    key = (bracket_size, m_seeds)
    if key not in SEED_TEMPLATES:  raise ValueError(f"No seeding template for {bracket_size}-draw with {m_seeds} seeds")
    seed_positions = SEED_TEMPLATES[key]
    seed_positions = randomize_seeds(seed_positions)
    
    key_bye = (n_players, m_seeds)
    try: bye_positions = BYE_TEMPLATES[key_bye]
    except KeyError: bye_positions = []
    
    draw = [None] * bracket_size
    for seed_num, pos in enumerate(seed_positions, start=1):
        draw[pos - 1] = [seed_num,seed_num]
        
    for seed_num, pos in enumerate(bye_positions, start=1):
        draw[pos - 1] = [np.nan,np.nan]

    remaining = [[i,np.nan] for i in range(1, n_players + 1) if i > m_seeds]
    random.shuffle(remaining)

    idx = 0
    for i in range(bracket_size):
        if draw[i] is None:
            if idx < len(remaining):
                draw[i] = remaining[idx]
                idx += 1
            else:
                draw[i] = [np.nan,np.nan]

    draw = pd.DataFrame(draw, columns=['Rank','Seed'])
    return draw

def elo_to_win(ra,rb):
    win_a = 1/(1+pow(10,(rb-ra)/400))
    win_b = 1/(1+pow(10,(ra-rb)/400))
    return win_a, win_b

def p_to_pts(df,level):
    POINTS_TOURNAMENT = {
        (128): [2000, 1200, 720, 360, 180, 90, 45, 10],
        (96):  [1000, 650, 400, 200, 100, 50, 30, 10],
        (56):  [1000, 650, 400, 200, 100, 50, 10, 0],
        (48):  [500, 330, 180, 90, 45, 20, 0, 0],
        (32):  [500, 330, 180, 90, 45, 25, 0, 0],
        (16):  [250, 165, 100, 50 ,25, 0, 0, 0],
    }
    scoring = POINTS_TOURNAMENT[level]
    try: df['xPts'] += scoring[0] * df['R1'] 
    except: df
    try: df['xPts'] += scoring[1] * (df['R2']-df['R1'])
    except: df
    try: df['xPts'] += scoring[2] * (df['R4']-df['R2'])
    except: df
    try: df['xPts'] += scoring[3] * (df['R8']-df['R4'])
    except: df
    try: df['xPts'] += scoring[4] * (df['R16']-df['R8'])
    except: df
    try: df['xPts'] += scoring[5] * (df['R32']-df['R16'])
    except: df
    try: df['xPts'] += scoring[6] * (df['R64']-df['R32'])
    except: df
    try: df['xPts'] += scoring[7] * (df['R128']-df['R64'])
    except: df
    return df

def tournament_sim(pdata, player_count, seeds, print_results):
    draw = generate_tennis_draw(player_count, seeds)
    draw = draw.merge(pdata, left_on='Rank', right_on='ATP Rank', how='left')
    
    draw['Player'] = draw['Player'].fillna('BYE')
    draw['Elo'] = draw['Elo'].fillna(0)
    draw['Rank'] = draw['Rank'].fillna(2000)
    draw['ATP Rank'] = draw['ATP Rank'].fillna(2000)
    draw['Seed'] = draw['Seed'].fillna(1000)
    
    draw['xPts'] = 0
    draw[f'R{len(draw)}'] = 1

    active = len(draw)
    while(active>1):
        if(print_results==1): print(f'R{active//2}')
        draw[f'R{active//2}'] = 0
        p=0; target_index = draw[draw[f'R{int(active)}'] == 1].index.to_list()
        
        while(p<active):
            flag = random.random()
            player_1,player_2 = target_index[p:p+2]
            player_1_w,player_2_w = elo_to_win(draw.loc[player_1]['Elo'],draw.loc[player_2]['Elo'])
            
            if(flag >= player_1_w): 
                draw.loc[player_2, f'R{active//2}'] = 1
                
                if(draw.loc[player_1]['Seed']<draw.loc[player_2]['Seed']):
                    draw.loc[player_2, 'xPts'] += 20
                    draw.loc[player_1, 'xPts'] -= 20
                    
                if(print_results==1): print(draw.loc[player_2]['Player'],round(player_2_w,3),"beat",draw.loc[player_1]['Player'],round(player_1_w,3),round(1-flag,3))
            else: 
                draw.loc[player_1, f'R{active//2}'] = 1
                
                if(draw.loc[player_2]['Seed']<draw.loc[player_1]['Seed']):
                    draw.loc[player_1, 'xPts'] += 20
                    draw.loc[player_2, 'xPts'] -= 20
                    
                if(print_results==1): print(draw.loc[player_1]['Player'],round(player_1_w,3),"beat",draw.loc[player_2]['Player'],round(player_2_w,3),round(flag,3))
            
            p += 2       
        active //= 2
    draw = p_to_pts(draw,player_count)
    return draw

def monte_carlo_tournament_sims(iters, pdata, player_count, seeds, print_results):
    print("monte carlo sims started")
    start_time = datetime.now()
    i = 0; all_sims = []
    while(i<iters):
        sim_n = tournament_sim(pdata, player_count, seeds, print_results)
        all_sims.append(sim_n)
        i+=1
    
    all_sims = pd.concat(all_sims)
    column_names = all_sims.columns.to_list()
    required_columns = [i for i in column_names if i[0] == 'R']
    all_sims = all_sims.pivot_table(index=['Rank', 'Player', 'Elo'], 
                                  values = ['xPts', 'Seed'] + required_columns, 
                                  aggfunc="mean")
    all_sims = all_sims.reset_index()
    
    all_sims = all_sims[['Rank','Player','Elo','Seed']+required_columns+['xPts']]
    all_sims = all_sims[all_sims['Player']!='BYE']
    all_sims.loc[all_sims['Seed']==1000,'Seed'] = np.nan
    all_sims = all_sims.drop(columns=['Rank'])
    
    print("sim time in minutes",round((datetime.now()-start_time).total_seconds()/60,2))
    return all_sims
    
#%% extract data
#data = extract_tournament_draw('')
#data = p_to_pts(data,'1000')

player_data = extract_elo_data(0)

pdata = player_data[['Player',f'{surface}Elo','ATP Rank']]
pdata.columns = ['Player','Elo','ATP Rank']

pdata = pdata.sort_values(by='ATP Rank', ascending=True)
pdata['ATP Rank'] = range(1,len(pdata)+1)
#pdata['ATP Rank'] = pdata['ATP Rank'].fillna(2000)

#%% monte carlo sims

#draw = generate_tennis_draw(entrants, seeds)

#sim = tournament_sim(pdata, entrants, seeds, 1)

mc_sim = monte_carlo_tournament_sims(1000, pdata, entrants, seeds, 0)
