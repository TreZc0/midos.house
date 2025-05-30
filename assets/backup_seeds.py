#!/usr/bin/python3 -i

import datetime
import email.utils
import json
import pathlib
import re
import urllib.parse

import bs4 # Debian: python3-bs4, PyPI: beautifulsoup4
import psycopg # Debian: python3-psycopg, PyPI: psycopg[binary]
import requests # Debian: python3-requests, PyPI: requests

SEEDS_DIR = pathlib.Path('/var/www/midos.house/seed')

with open('/etc/xdg/midos-house.json') as config_f:
    config = json.load(config_f)

conn = psycopg.connect('dbname=midos_house user=mido')

def b(seed_id, room=None, *, race_id=None, startgg=None, async_room1=None, async_room2=None, async_room3=None, unlock=True):
    patch_resp = requests.get('https://ootrandomizer.com/patch/get', params={'id': seed_id})
    if patch_resp.status_code == 404:
        file_stem = input('file stem: ').strip()
    else:
        patch_resp.raise_for_status()
        file_stem = re.fullmatch('attachment; filename=(.*)\\.zpfz?', patch_resp.headers['Content-Disposition']).group(1)
        with open(SEEDS_DIR / re.fullmatch('attachment; filename=(.*\\.zpfz?)', patch_resp.headers['Content-Disposition']).group(1), 'wb') as patch_f:
            patch_f.write(patch_resp.content)
    api_resp = requests.get('https://ootrandomizer.com/api/v2/seed/details', params={'id': seed_id, 'key': config['ootrApiKey']})
    try:
        api_resp.raise_for_status()
    except requests.HTTPError:
        if race_id is not None or room is not None or startgg is not None or async_room1 is not None or async_room2 is not None or async_room3 is not None:
            page_resp = requests.get('https://ootrandomizer.com/seed/get', params={'id': seed_id})
            page_resp.raise_for_status()
            soup = bs4.BeautifulSoup(page_resp.text)
            creation_timestamp = f"{email.utils.parsedate_to_datetime(soup.find(id='parsedTimestamp').string).astimezone(datetime.timezone.utc):%Y-%m-%dT%H:%M:%SZ}"
            file_hash = [urllib.parse.unquote(re.match('^/img/hash/(.+)\\.png$', img.attrs['src']).group(1)) for img in soup.find(id='seedHashBox').find_all('img')]
        spoiler_resp = requests.get('https://ootrandomizer.com/spoilers/get', params={'id': seed_id})
        if spoiler_resp.status_code != 400: # returns error 400 if no spoiler log has been generated
            spoiler_resp.raise_for_status()
            with open(SEEDS_DIR / f'{file_stem}_Spoiler.json', 'wb') as spoiler_f:
                spoiler_f.write(spoiler_resp.content)
    else:
        if api_resp.json()['spoilerLog'] is None and unlock:
            requests.post('https://ootrandomizer.com/api/v2/seed/unlock', params={'key': config['ootrApiKey'], 'id': seed_id}).raise_for_status()
            api_resp = requests.get('https://ootrandomizer.com/api/v2/seed/details', params={'id': seed_id, 'key': config['ootrApiKey']})
            api_resp.raise_for_status()
        creation_timestamp = api_resp.json()['creationTimestamp']
        if api_resp.json()['spoilerLog'] is None:
            file_hash = None
        else:
            with open(SEEDS_DIR / f'{file_stem}_Spoiler.json', 'w') as spoiler_f:
                spoiler_f.write(api_resp.json()['spoilerLog'])
            file_hash = json.loads(api_resp.json()['spoilerLog'])['file_hash']
    with conn.cursor() as cur:
        try:
            if race_id is not None:
                if race_id >= 2 ** 63:
                    race_id -= 2 ** 64
                cur.execute("""UPDATE races SET
                    web_id = %s,
                    web_gen_time = %s,
                    file_stem = %s,
                    hash1 = %s,
                    hash2 = %s,
                    hash3 = %s,
                    hash4 = %s,
                    hash5 = %s
                WHERE id = %s""", (seed_id, creation_timestamp, file_stem, *file_hash, race_id))
            if room is not None:
                cur.execute("""UPDATE races SET
                    web_id = %s,
                    web_gen_time = %s,
                    file_stem = %s,
                    hash1 = %s,
                    hash2 = %s,
                    hash3 = %s,
                    hash4 = %s,
                    hash5 = %s
                WHERE room = %s""", (seed_id, creation_timestamp, file_stem, *file_hash, room))
            if startgg is not None:
                cur.execute("""UPDATE races SET
                    web_id = %s,
                    web_gen_time = %s,
                    file_stem = %s,
                    hash1 = %s,
                    hash2 = %s,
                    hash3 = %s,
                    hash4 = %s,
                    hash5 = %s
                WHERE startgg_set = %s""", (seed_id, creation_timestamp, file_stem, *file_hash, startgg))
            if async_room1 is not None:
                cur.execute("""UPDATE races SET
                    web_id = %s,
                    web_gen_time = %s,
                    file_stem = %s,
                    hash1 = %s,
                    hash2 = %s,
                    hash3 = %s,
                    hash4 = %s,
                    hash5 = %s
                WHERE async_room1 = %s""", (seed_id, creation_timestamp, file_stem, *file_hash, async_room1))
            if async_room2 is not None:
                cur.execute("""UPDATE races SET
                    web_id = %s,
                    web_gen_time = %s,
                    file_stem = %s,
                    hash1 = %s,
                    hash2 = %s,
                    hash3 = %s,
                    hash4 = %s,
                    hash5 = %s
                WHERE async_room2 = %s""", (seed_id, creation_timestamp, file_stem, *file_hash, async_room2))
            if async_room3 is not None:
                cur.execute("""UPDATE races SET
                    web_id = %s,
                    web_gen_time = %s,
                    file_stem = %s,
                    hash1 = %s,
                    hash2 = %s,
                    hash3 = %s,
                    hash4 = %s,
                    hash5 = %s
                WHERE async_room3 = %s""", (seed_id, creation_timestamp, file_stem, *file_hash, async_room3))
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
