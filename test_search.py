#!/usr/bin/env python3
import yt_dlp

def search_music(query):
    search_query = f'{query} audio'
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        results = ydl.extract_info(f'ytsearch1:{search_query}', download=False)
        if results and 'entries' in results and results['entries']:
            entry = results['entries'][0]
            url = f"https://www.youtube.com/watch?v={entry.get('id')}"
            title = entry.get('title')
            print(f'Title: {title}')
            print(f'URL:   {url}')
            return url
    print('No results')
    return None

if __name__ == '__main__':
    while True:
        try:
            query = input('> ')
            if query.strip():
                search_music(query)
                print()
        except (EOFError, KeyboardInterrupt):
            break
