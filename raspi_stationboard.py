#!/usr/bin/env python3
import datetime
from collections import defaultdict
from typing import NamedTuple, List, Dict, Any

import requests
import time
import scrollphathd

API_URL = 'https://fahrplan.search.ch/api/stationboard.json'


FETCH_PERIOD_S = 30
SHOW_N_CONNECTIONS = 2
STOPS = [
    {
        'name': 'Zürich, Brunau/Mutschellenstr.',
        'terminals': {
            '72': ['Zürich, Milchbuck', 'Zürich, Albisriederplatz']
        },
        'time_to_station_s': 320 / (6.5 / 3.6) + 60  # 320m
    },
    {
        'name': 'Zürich, Brunaustrasse',
        'terminals': {
            '7': ['Stettbach, Bahnhof'],
            '8': ['Zürich, Hardturm'],
            '13': ['Zürich, Albisgütli']
        },
        'time_to_station_s': 320 / (6.5 / 3.6) + 60  # 290m
    }
]


class Connection(NamedTuple):
    line: str
    stop: str
    terminal: str
    time: datetime.datetime
    delay_min: int


def get_stationboard(stop: str) -> dict:
    resp = requests.get(API_URL, params=dict(stop=stop,
                                             limit=20,
                                             show_delays=1,
                                             mode='depart',
                                             transportation_types='tram,bus'))
    data = resp.json()
    assert 'connections' in data, Exception(f'API error: {" ".join(data["messages"])}')
    return data


def get_connections_for_stop(stop: dict) -> List[Connection]:
    data = get_stationboard(stop['name'])
    for conn in data['connections']:
        # we don't care about this line
        if not conn['line'] in stop['terminals'].keys():
            continue
        # wrong direction
        terminal = conn['terminal']['name']
        if not terminal in stop['terminals'][conn['line']]:
            continue
        name = f'{conn["*G"][0]}{conn["*L"]}'
        timestamp = datetime.datetime.strptime(conn['time'], '%Y-%m-%d %H:%M:%S')
        if 'dep_delay' in conn:
            delay = int(conn['dep_delay'].strip('+'))
        else:
            delay = 0
        yield Connection(name, data['stop']['name'], terminal, timestamp, delay)


def fetch_connections_per_line(stops: List[Dict[str, Any]]) -> Dict[str, List[Connection]]:
    conns_per_line = defaultdict(lambda: [])
    for stop in stops:
        for conn in get_connections_for_stop(stop):
            conns_per_line[conn.line].append(conn)
    return dict(conns_per_line)


def connections_for_display(connections: List[Connection], stops: List[Dict[str, Any]]):
    now = datetime.datetime.now()
    for connection in connections:
        stop = [s for s in stops if s['name'] == connection.stop][0]

        # check if we can still catch this one
        departure_with_delay = connection.time + datetime.timedelta(minutes=connection.delay_min)
        walk_arrive_at_stop = now + datetime.timedelta(seconds=stop['time_to_station_s']) * 0.8
        if walk_arrive_at_stop > departure_with_delay:
            continue

        dt = connection.time - now
        if connection.delay_min != 0:
            yield f'{int(dt.seconds / 60)}+{connection.delay_min}'
        else:
            yield f'{int(dt.seconds / 60)}'


def display_line_with_scroll(text: str):
    print(text)

    scrollphathd.clear()
    length = scrollphathd.write_string(text, brightness=0.4)
    scrollphathd.show()
    time.sleep(0.7)

    for _ in range(length - 17):
        scrollphathd.scroll()
        scrollphathd.show()
        time.sleep(0.025)
    time.sleep(0.4)


def main():
    last_update = 0
    conns_per_line = None
    while True:
        # fetch, if necessary
        if time.monotonic() > last_update + FETCH_PERIOD_S:
            # noinspection PyBroadException
            try:
                conns_per_line = fetch_connections_per_line(STOPS)
                last_update = time.monotonic()
            except:
                conns_per_line = None

        if conns_per_line is None:
            display_line_with_scroll('no connection')
            continue

        # now, display
        for line, connection in conns_per_line.items():
            conns = list(connections_for_display(connection, STOPS))
            text = f'{line} ' + ' '.join(conns[:SHOW_N_CONNECTIONS])
            display_line_with_scroll(text)


if __name__ == "__main__":
    main()