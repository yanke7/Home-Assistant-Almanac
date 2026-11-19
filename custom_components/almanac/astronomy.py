"""Local approximate astronomy shared in behavior with the Almanac card.

Angles follow the card's geocentric model (with lunar parallax correction).
Not intended for navigation or precision ephemerides. All wire times are UTC ms.
"""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from math import acos, asin, atan2, cos, isfinite, pi, sin, tan
from zoneinfo import ZoneInfo

R = pi / 180
DAY = 86400000
STEP = 120000
OBL = R * 23.4397
UTC = timezone.utc
NAMES = ('New moon', 'Waxing crescent', 'First quarter', 'Waxing gibbous', 'Full moon', 'Waning gibbous', 'Last quarter', 'Waning crescent')


def days(t):
    return t / DAY - 0.5 + 2440588 - 2451545


def ra(l, b):
    return atan2(sin(l) * cos(OBL) - tan(b) * sin(OBL), cos(l))


def dec(l, b):
    return asin(sin(b) * cos(OBL) + cos(b) * sin(OBL) * sin(l))


def sun_coords(d):
    m = R * (357.5291 + 0.98560028 * d)
    l = m + R * (1.9148 * sin(m) + 0.02 * sin(2*m) + 0.0003 * sin(3*m)) + R * 102.9372 + pi
    return {'ra': ra(l, 0), 'dec': dec(l, 0)}


def moon_coords(d):
    l = R * (218.316 + 13.176396*d)
    m = R * (134.963 + 13.064993*d)
    f = R * (93.272 + 13.229350*d)
    l += R * 6.289 * sin(m)
    b = R * 5.128 * sin(f)
    return {'ra': ra(l,b), 'dec': dec(l,b), 'dist': 385001 - 20905*cos(m)}


def place(c,t,lat,lon):
    phi = R*lat
    h = R*(280.16 + 360.9856235*days(t)) + R*lon - c['ra']
    alt = asin(sin(phi)*sin(c['dec']) + cos(phi)*cos(c['dec'])*cos(h))
    az = atan2(sin(h), cos(h)*sin(phi)-tan(c['dec'])*cos(phi)) + pi
    pa = atan2(sin(h), tan(phi)*cos(c['dec'])-sin(c['dec'])*cos(h))
    return {'alt':alt/R, 'az':(az/R)%360, 'pa':pa}


def sun_at(t,lat,lon):
    return place(sun_coords(days(t)),t,lat,lon)


def moon_at(t,lat,lon):
    c = moon_coords(days(t))
    p = place(c,t,lat,lon)
    p['alt'] -= 0.95*cos(p['alt']*R)
    p['dist'] = c['dist']
    return p


def illumination(t):
    d = days(t);s = sun_coords(d);m = moon_coords(d)
    phi = acos(max(-1,min(1,sin(s['dec'])*sin(m['dec'])+cos(s['dec'])*cos(m['dec'])*cos(s['ra']-m['ra']))))
    inc = atan2(149598000*sin(phi),m['dist']-149598000*cos(phi))
    ang = atan2(cos(s['dec'])*sin(s['ra']-m['ra']),sin(s['dec'])*cos(m['dec'])-cos(s['dec'])*sin(m['dec'])*cos(s['ra']-m['ra']))
    return {'f':(1+cos(inc))/2, 'phase':0.5+0.5*inc*(-1 if ang<0 else 1)/pi, 'ang':ang}


def phase_name(p):
    for i in range(4):
        d = abs(p-i/4)
        if min(d,1-d)<0.018:
            return NAMES[i*2]
    return NAMES[min(7,int(p*4)*2+1)]


@lru_cache(maxsize=256)
def start_of_date(date, tz):
    """Find the first instant of a local date, including midnight DST jumps."""
    target = datetime(date.year,date.month,date.day,tzinfo=UTC).timestamp()*1000
    lo,hi = int(target-DAY),int(target+DAY)
    zone = ZoneInfo(tz)
    while hi-lo>1:
        mid=(lo+hi)//2
        if datetime.fromtimestamp(mid/1000,zone).date()<date:
            lo=mid
        else:
            hi=mid
    return hi


def crossings(times,values,threshold):
    result=[]
    for i in range(1,len(values)):
        p,q=values[i-1]-threshold,values[i]-threshold
        if (p<0)!=(q<0):
            result.append({'t':times[i-1]+(times[i]-times[i-1])*p/(p-q),'up':q>=0})
    return result


@lru_cache(maxsize=16)
def day_data(date,lat,lon,tz):
    d0=start_of_date(date,tz);end=start_of_date(date+timedelta(days=1),tz)
    times=list(range(d0,end,STEP))+[end]
    sun=[sun_at(t,lat,lon) for t in times];moon=[moon_at(t,lat,lon) for t in times]
    sa=[p['alt'] for p in sun];ma=[p['alt'] for p in moon]
    h=crossings(times,sa,-0.833);c=crossings(times,sa,-6);g=crossings(times,sa,6)
    def first(events,up):
        return next((e['t'] for e in events if e['up']==up),None)
    noon=max(range(len(sa)),key=sa.__getitem__)
    # Integrate time above the horizon, also for days with only one crossing.
    length=0;since=d0 if sa[0]>=-0.833 else None
    for e in h:
        if e['up']: since=e['t']
        elif since is not None: length+=e['t']-since;since=None
    if since is not None: length+=end-since
    return {'d0':d0,'end':end,'t':times,'sa':sa,'ma':ma,
            'sz':[p['az'] for p in sun],'mz':[p['az'] for p in moon],
            'rise':first(h,True),'set':first(list(reversed(h)),False),
            'dawn':first(c,True),'dusk':first(list(reversed(c)),False),
            'golden':first(list(reversed(g)),False),'noon':times[noon],
            'noonAlt':sa[noon],'moonEv':crossings(times,ma,-0.833),'len':length}


def snapshot(now,latitude,longitude,time_zone):
    """Return sensors and the card's chart snapshot for one home location."""
    if now.tzinfo is None:
        raise ValueError('now must be timezone-aware')
    if not (isfinite(latitude) and -90<=latitude<=90 and isfinite(longitude) and -180<=longitude<=180):
        raise ValueError('Invalid latitude or longitude')
    zone=ZoneInfo(time_zone);date=now.astimezone(zone).date();t=now.timestamp()*1000
    charts=[day_data(date+timedelta(days=i),latitude,longitude,time_zone) for i in range(-1,3)]
    s=sun_at(t,latitude,longitude);m=moon_at(t,latitude,longitude);il=illumination(t)
    today=charts[1]
    def upcoming(key):
        return next((d[key] for d in charts[1:] if d[key] is not None and d[key]>t),None)
    def lunar(up):
        return next((e['t'] for d in charts[1:] for e in d['moonEv'] if e['up']==up and e['t']>t),None)
    values={'sun_elevation':s['alt'],'sun_azimuth':s['az'],'moon_elevation':m['alt'],'moon_azimuth':m['az'],
            'moon_illumination':il['f']*100,'moon_phase':phase_name(il['phase']).lower().replace(' ','_'),
            'moon_age':il['phase']*29.53,'moon_distance':m['dist'],
            'daylight_duration':today['len']/60000,'daylight_change':(today['len']-charts[0]['len'])/1000,
            'sky_period':'day' if s['alt']>6 else 'golden' if s['alt']>-4 else 'twilight' if s['alt']>-12 else 'night',
            'sun_above_horizon':s['alt']>-0.833,'moon_above_horizon':m['alt']>-0.833,
            'next_moonrise':lunar(True),'next_moonset':lunar(False)}
    for name,key in [('next_sunrise','rise'),('next_sunset','set'),('next_dawn','dawn'),('next_dusk','dusk'),('next_solar_noon','noon'),('next_golden_hour','golden')]:
        values[name]=upcoming(key)
    return {'now':t,'location':{'latitude':latitude,'longitude':longitude,'time_zone':time_zone},
            'sun':s,'moon':m,'illumination':il,'days':charts,'values':values}
