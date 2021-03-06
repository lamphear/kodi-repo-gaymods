import os.path as path
import base64
import json
import re
import urllib
from urllib import quote_plus
import ssl
import requests
import webutil as WebUtils
from kodiswift import Plugin, xbmc, ListItem

urlresolver = None
try:
    import resolveurl as urlresolver
except:
    try:
        import urlresolver as urlresolver
    except:
        urlresolver = None

plugin = Plugin()
ssl._create_default_https_context = ssl._create_unverified_context
__BASEURL__ = 'https://watchseries-online.be'
__addondir__ = xbmc.translatePath(plugin.addon.getAddonInfo('path'))
__datadir__ = xbmc.translatePath('special://profile/addon_data/{0}/'.format(plugin.id))
__cookie__ = path.join(__datadir__, 'cookies.lwp')
__temp__ = path.join(__datadir__, 'temp/')
__resdir__ = path.join(__addondir__, 'resources')
__imgsearch__ = path.join(__resdir__, 'search.png')
__savedjson__ = path.join(xbmc.translatePath(plugin.addon.getAddonInfo('profile')), 'savedshows.json')
getWeb = WebUtils.CachedWebRequest(path.join(__datadir__, 'cookies.lwp'), __temp__)

# Category Could be changed to use Category Sitemap
# https://watchseries-online.be/category-sitemap.xml


@plugin.route('/')
def index():
    litems = []
    plugin.set_content('episodes')
    imgtpl = __imgsearch__.replace('search.png','folder-{0}.png')
    imglatest = imgtpl.format('latest')
    imgplay = imgtpl.format('play')
    imgcat = imgtpl.format('cat')
    imgsearch = imgtpl.format('search')
    imgother = imgtpl.format('blank')
    itemlatest = {'label': 'Latest Episodes', 'icon': imglatest, 'thumbnail': imglatest,
                  'path': plugin.url_for(latest, offset=0, urlpath='last-350-episodes')}
    itemplay = {'label': 'Play URL [I](Try\'s Finding Playable Source with [B]ResolveURL Module[/B][/I])[/I]',
                'icon': imgplay, 'thumbnail': imgplay, 'path': plugin.url_for(endpoint=resolveurl)}
    itemcategory= {'label': 'Category', 'icon': imgcat, 'thumbnail': imgcat,
                   'path': plugin.url_for(search, dopaste=False)}
    itemsearch = {'label': 'Search', 'icon': imgsearch, 'thumbnail': imgsearch,
                  'path': plugin.url_for(search, dopaste=bool(False))}
    itemothers = {'label': 'Other Shows', 'icon': imgother, 'thumbnail': imgother,
                   'path': plugin.url_for(category, name="not-in-homepage", url="category/not-in-homepage")}
    itemsaved = {'label': '[COLOR red][I]Saved Shows (Broken)[/I][/COLOR]', 'path': plugin.url_for(saved), 'icon': 'DefaultFolder.png',
                 'thumbnail': 'DefaultFolder.png'}
    # itemsearchpasted = {'label': 'Search (Paste Clipboard)', 'icon': __imgsearch__, 'thumbnail': __imgsearch__, 'path': plugin.url_for(search, paste=True)}
    litems.append(itemlatest)
    litems.append(itemplay)
    litems.append(itemcategory)
    litems.append(itemsearch)
    litems.append(itemothers)
    #litems.append(itemsaved)
    return litems


def DL(url):
    html = u''
    getWeb = WebUtils.CachedWebRequest(path.join(__datadir__, 'cookies.lwp'), __temp__)
    html = getWeb.getSource(url, form_data=None, referer=__BASEURL__, xml=False, mobile=False).encode('latin', errors='ignore')
    return html


def makecatitem(name, link, removelink=False):
    item = {}
    ctxitem = {}
    itempath = plugin.url_for(category, name=name, url=link)
    item = {'label': name, 'label2': link, 'icon': 'DefaultFolder.png', 'thumbnail': 'DefaultFolder.png',
            'path': itempath}
    item.setdefault(item.keys()[0])
    litem = ListItem.from_dict(**item)
    # if removelink:
    #    litem.add_context_menu_items([('Remove Saved Show', 'RunPlugin("{0}")'.format(plugin.url_for(removeshow, name=name, link=itempath)),)])
    # else:
    litem.add_context_menu_items(
        [('Save Show', 'RunPlugin("{0}")'.format(plugin.url_for(saveshow, name=name, link=link)),)])
    return litem


def episode_makeitem(episodename, episodelink, dateadded=None):
    '''
    Will return a ListItem for the given link to an episode and it's full linked name.
    Name will be sent to format show to attempt to parse out a date or season from the title.
    Infolabels are populated with any details that can be parsed from the title as well.
    Should be used anytime an item needs to be created that is an item for one specific episode of a show.
    Latest 350, Saved Show, Category (Show listing of all episodes for that series) would all use this.
    '''
    infolbl = {}
    sourcespath = plugin.url_for(episode, name=episodename, url=episodelink)
    img = "DefaultVideoFolder.png"
    seasonstr = ''
    try:
        eptitle, epdate, epnum = formatshow(episodename)
        eplbl = formatlabel(eptitle, epdate, epnum)
        plotstr = "{0} ({1}): {2} {3}".format(epdate, epnum, eptitle, episodelink)
        epdate = epdate.strip('-')
        try:
            import dateutil
            asdate = dateutil.parser.parse(epdate)
            premdate = asdate.isoformat().split('T',1)[0]
        except:
            premdate = "2000-01-01"
        infolbl = {'Premiered': premdate, 'TVShowTitle': eptitle, 'Plot': plotstr}
        if len(epnum) > 0:
            showS, showE = findepseason(epnum)
            snum = int(showS)
            epnum = int(showE)
            infolbl.update({'Episode': showE, 'Season': showS})
            if snum > 0 and epnum > 0:
                epdate = "S{0}e{1}".format(snum, epnum)
                infolbl.update({'PlotOutline': epdate})
        #sourcespath = plugin.url_for(episode, name=episodename, url=episodelink)
        playpath = plugin.url_for(endpoint=playfirst, url=episodelink.encode('utf-8', 'ignore'))
        item = {'label': eplbl, 'label2': epdate, 'icon': img, 'thumbnail': img, 'path': playpath.encode('utf-8', 'ignore')}
        item.setdefault(item.keys()[0])
        li = ListItem.from_dict(**item)
        li.set_is_playable(is_playable=True)
        li.is_folder = False
        li.set_info(info_type='video', info_labels=infolbl)
        #li.add_context_menu_items([('Sources', 'RunPlugin("{0}")'.format(sourcespath),)])
        #[('Autoplay', 'RunPlugin("{0}")'.format(plugin.url_for(endpoint=playfirst, url=episodelink)),)])
    except:
        li = ListItem(label=episodename, label2=episodelink, icon=img, thumbnail=img, path=sourcespath)
    return li


def formatshow(name=""):
    epname = name.replace('&#8211;', '-')
    epnum = ''
    epname = ''
    epdate = ''
    numparts = re.compile(r'[Ss]\d+[Ee]\d+').findall(name)
    if len(numparts) > 0:
        epnum = numparts.pop()
    datematch = re.compile(r'[12][0-9][0-9][0-9].[0-9][0-9]?.[0-9][0-9]?').findall(name)
    if len(datematch) > 0:
        epdate = datematch[0]
    name = name.replace('  ', ' ').strip()
    name = name.replace(epnum, '').strip()
    name = name.replace(epdate, '').strip()
    if epdate == '':
        # Let's see if we can find the date in the form of a string of Month_Abbr Daynum Year
        try:
            from calendar import month_abbr, month_name
            monthlist = month_name[:]
            monthlist.extend(month_abbr)
            monthlist.pop(13)
            monthlist.pop(0)
            regex = "{0}.(\d\d).(\d\d\d\d)"
            nummonth = 1
            for mon in monthlist:
                matches = re.compile(regex.format(mon)).findall(name)
                if len(matches) > 0:
                    day, year = matches.pop()
                    if nummonth < 10:
                        epdate = "{0} 0{1} {2}".format(year, nummonth, day)
                    else:
                        epdate = "{0} {1} {2}".format(year, nummonth, day)
                    name = name.replace(mon, '').strip()
                    name = name.replace(year, '').strip()
                    name = name.replace(day, '').strip()
                    break
                nummonth += 1
                if nummonth > 12: nummonth = 1
            if epdate == '':
                year = re.split(r'\d\d\d\d', name, 1)[0]
                epdate = name.replace(year, '').strip()
                name = name.replace(epdate, '').strip()
        except:
            pass
    epname = name.replace('(', '').replace(')', '').strip()
    epdate = epdate.replace('(', '').replace(')', '').strip()
    epnum = epnum.replace('(', '').replace(')', '').strip()
    return epname.strip(), epdate.strip(), epnum.strip()


def formatlabel(epname, epdate, epnum):
    eplbl = ''
    epname = epname.replace('!', '')
    try:
        if len(epdate) == 0 and len(epnum) == 0:
            return epname
        else:
            if len(epdate) > 0 and len(epnum) > 0:
                eplbl = "{0} ([COLOR blue]{1}[/COLOR] [COLOR cyan]{2}[/COLOR])".format(epname, epdate, epnum)
            else:
                if len(epdate) > 0:
                    eplbl = "{0} ([COLOR blue]{1}[/COLOR])".format(epname, epdate)
                else:
                    eplbl = "{0} ([COLOR cyan]{1}[/COLOR])".format(epname, epnum)
    except:
        eplbl = epname + ' ' + epdate + ' ' + epnum
    return eplbl


def findepseason(epnum):
    numseason = ''
    numep = ''
    parts = epnum.lower().split('e', 1)
    numseason = parts[0].replace('s', '').strip()
    numep = parts[-1].replace('e', '').strip()
    return numseason, numep


def filterout(text, filtertxt=''):
    filterwords = []
    if len(filtertxt) < 1:
        return False
    if filtertxt.find(',') != -1:
        filterwords = filtertxt.lower().split(',')
    else:
        return False
    if text.lower() in filterwords:
        return True
    return False


def find_episodes(fullhtml='', noDate=False):
    html = fullhtml.partition("</nav>")[-1].split("</ul>", 1)[0]
    strDate = ur"<li class='listEpisode'>(\d+ \d+ \d+) : "
    strUrl = ur'<a.+?href="([^"]*?)">'
    strName = ur'</span>([^<]*?)</a>'
    regexstr = "{0}{1}.+?{2}".format(strDate, strUrl, strName)
    if noDate:
        regexstr = "{0}.+?{1}".format(strUrl, strName)
    matches = re.compile(regexstr).findall(html)
    epdate = ''
    eptitle = ''
    litems = []
    if noDate:
        for eplink, epname in matches:
            item = episode_makeitem(epname, eplink)
            item.set_path(plugin.url_for(episode, name=epname, url=eplink))
            litems.append(item)
    else:
        for epdate, eplink, epname in matches:
            item = episode_makeitem(epname, eplink, epdate)
            item.set_path(plugin.url_for(episode, name=epname, url=eplink))
            dateout = epdate.replace(' ', '-').strip()
            item.label += " [I][B][COLOR orange]{0}[/COLOR][/B][/I]".format(dateout)
            litems.append(item)
    return litems


def findvidlinks(html='', findhosts=[]):
    matches = re.compile(ur'<div class="play-btn">.*?</div>', re.DOTALL).findall(html)
    vids = []
    filtered = []
    findhost = findhosts[0]
    if findhost is not None:
        findhost = findhost.lower()
    for link in matches:
        url = re.compile(ur'href="(.+)">', re.DOTALL + re.S).findall(str(link))[0]
        if url is not None:
            if url.find('linkOut') != -1:
                urlout = url.split('?id=')[-1]
                url = base64.b64decode(urlout)            
            host = str(url.lower().split('://', 1)[-1])
            host = host.replace('www.', '')
            #host = host.partition('.')[1:]
            host = str(host.split('.', 1)[0]).title()
            label = "{0} [COLOR blue]{1}[/COLOR]".format(host, url.rpartition('/')[-1])
            vids.append((label, url,))
            for findhost in findhosts:
                if url.lower().find(findhost.lower()) != -1:
                    filtered.append((label, url,))
    vids.sort()
    if len(filtered) < 1:
        return vids
    else:
        filtered.sort()
        return filtered


def sortSourceItems(litems=[]):
    try:
        litems.sort(key=lambda litems: litems['label'], reverse=False)
        sourceslist = []
        stext = plugin.get_setting('topSources')
        if len(stext) < 1:
            sourceslist.append('thevideo')
            sourceslist.append('movpod')
            sourceslist.append('daclip')
        else:
            sourceslist = stext.split(',')
        sorteditems = []
        for sortsource in sourceslist:
            for item in litems:
                if str(item['label2']).find(sortsource) != -1: sorteditems.append(item)
        for item in sorteditems:
            try:
                litems.remove(item)
            except:
                pass
        sorteditems.extend(litems)
        return sorteditems
    except:
        plugin.notify(msg="ERROR SORTING: #{0}".format(str(len(litems))), title="Source Sorting", delay=20000)
        return litems


def loadsaved():
    sitems = []
    litems = []
    items = []
    savedpath = ''
    try:
        savedpath = path.join(__datadir__, "saved.json")
        if path.exists(savedpath):
            fpin = file(savedpath)
            rawjson = fpin.read()
            sitems = json.loads(rawjson)
            fpin.close()
        else:
            return []
        for item in sitems:
            li = ListItem.from_dict(**item)
            li.add_context_menu_items(
                [('Remove Saved Show',
                  'RunPlugin("{0}")'.format(plugin.url_for(removeshow, name=li.label, link=li.path)),)])
            litems.append(li)
    except:
        pass
    return litems


@plugin.route('/saved')
def saved():
    litems = []
    sitems = []
    sitems = loadsaved()
    noitem = {'label': "No Saved Shows", 'icon': 'DefaultFolder.png', 'path': plugin.url_for('index')}
    if len(sitems) < 1:
        return [noitem]
    else:
        return sitems


@plugin.route('/saveshow/<name>/<link>')
def saveshow(name='', link=''):
    sitems = []
    litems = []
    try:
        savedpath = path.join(__datadir__, "saved.json")
        if path.exists(savedpath):
            fpin = file(savedpath)
            rawjson = fpin.read()
            sitems = json.loads(rawjson)
            fpin.close()
        saveitem = {'label': name, 'path': plugin.url_for(endpoint=category, name=name, url=link)}
        saveitem.setdefault(saveitem.keys()[0])
        sitems.insert(0, saveitem)
        fpout = file(savedpath, mode='w')
        json.dump(sitems, fpout)
        fpout.close()
        plugin.notify(msg="SAVED {0}".format(name), title=link)
    except:
        plugin.notify(msg="ERROR save failed for {0}".format(name), title=link)


@plugin.route('/saveshowfromepisode/<name>/<link>')
def saveshowfromepisode(name='', link=''):
    '''
    Loads the episode page and searches html for the category for the entire show not this specific episode to then save the show using the same show function used when we alreaedy know the category.
    <span class="info-category"><a href="https://watchseries-online.pl/category/late-night-with-seth-meyers" rel="category tag">Late Night with Seth Meyers</a></span>
    '''
    html = DL(link)
    matches = re.compile(ur'span class="info-category">.+?href="(http.+?[^"])".+?>(.+?[^<])</a>',
                         re.DOTALL + re.S + re.U).findall(html)
    litems = []
    categorylink = ''
    showname = ''
    if matches is not None:
        for showlink, catname in matches:
            categorylink = showlink
            showname = catname
        saveshow(name=showname, link=categorylink)


@plugin.route('/removeshow/<name>/<link>')
def removeshow(name='', link=''):
    sitems = []
    litems = []
    sitems = loadsaved()
    for item in sitems:
        if item.get('name') == name or item.get('link') == link:
            plugin.notify(title='Removed {0}'.format(name), msg='Removed "{0}": {1}'.format(name, link))
        else:
            litems.append(item)
    jsout = json.dumps(litems)
    plugin.addon.setSetting('savedshows', jsout)
    plugin.notify(title='Removed {0}'.format(name), msg='{0} Removed Show link: {1}'.format(name, link))


@plugin.route('/latest/<offset>/<urlpath>')
def latest(offset=0, urlpath='last-350-episodes'):
    url = __BASEURL__ + '/' + urlpath  # '/last-350-episodes'
    fullhtml = DL(url)
    html = fullhtml.partition("<ul class='listEpisodes'>")[-1].split("</ul>",1)[0].strip()
    regex = re.compile('<li>(.+?): <a href="([^"]*?)".+?>(.+?)</a> ')
    matches = regex.findall(html) #re.compile(regexstr).findall(html)
    litems = []
    epdate = ''
    eptitle = ''
    filtertxt = plugin.get_setting('filtertext')
    itemnext = {'label': 'Next ->', 'icon': 'DefaultFolder.png', 'thumbnail': 'DefaultFolder.png',
                'path': plugin.url_for(latest, offset=int(offset) + 400, urlpath=urlpath)}
    if len(matches) > 500:
        matches = matches[0:500]
    for epdate, eplink, epname in matches:
        # if not filterout(epname, filtertxt):
        item = episode_makeitem(epname, eplink, epdate)
        dateout = epdate.replace(' ', '-').strip()
        epnum = str(eplink.rpartition('-')[-1])
        if epnum == '2':
            epnum = str(eplink.replace('-{0}'.format(epnum),'').rpartition('-')[-1])
            epnumtext = "[COLOR red]{0}[/COLOR] v2".format(epnum.upper())
        elif epnum.upper().find('S') == -1 and epnum.upper().find('E') == -1:
            epnum = str(epname.rpartition('(')[-1]).rstrip(')').strip().replace(' ', '-')
            epnumtext = "[COLOR yellow]{0}[/COLOR]".format(epnum.upper())
        else:
            epnumtext = "[COLOR yellow]{0}[/COLOR]".format(epnum.upper())
        name = epname.replace(epnum, '').replace(epnum.upper(), '').strip()
        #item.label += " [I][B][COLOR orange]{0}[/COLOR][/B][/I]".format(dateout)
        item.label = "[COLOR white][B]{0}[/B][/COLOR] {1} [I][COLOR orange]{2}[/COLOR][/I]".format(name, epnumtext, dateout)
        litems.append(item)
    litems.append(itemnext)
    return litems


@plugin.route('/search/<dopaste>')
def search(dopaste=False):
    searchtxt = ''
    searchtxt = plugin.get_setting('lastsearch')
    searchtxt = plugin.keyboard(searchtxt, 'Search Watchseries-Online', False)
    if len(searchtxt) > 1:
        plugin.set_setting(key='lastsearch', val=searchtxt)
        #return query(searchquery=searchtxt)
        #return query(searchquery=searchtxt)
        caturl = '/category/' + searchtxt.replace(' ', '-')
        return category(name=searchtxt, url=caturl)
    else:
        return []


@plugin.route('/query/<searchquery>')
def query(searchquery):
    if searchquery.find(' ') != -1:
        searchquery = searchquery.replace(' ', '+')
    urlsearch = __BASEURL__ + '/?s={0}&search='.format(quote_plus(searchquery))
    fullhtml = DL(urlsearch)
    html = fullhtml
    htmlres = html.partition('<div class="ddmcc">')[2].split('</div>', 1)[0]
    matches = re.compile(ur'href="(https?.+?watchseries-online\.[a-z]+/category.+?[^"])".+?[^>]>(.+?[^<])<.a>',
                         re.DOTALL + re.S + re.U).findall(htmlres)
    litems = []
    for slink, sname in matches:
        litems.append(makecatitem(sname, slink))
    html = fullhtml.partition("</nav>")[-1].split("</ul>", 1)[0]
    strDate = ur"<li class='listEpisode'>(\d+ \d+ \d+) : "
    strUrl = ur'<a.+?href="([^"]*?)">'
    strName = ur'</span>([^<]*?)</a>'
    regexstr = "{0}{1}.+?{2}".format(strDate, strUrl, strName)
    matches = re.compile(regexstr).findall(html)
    epdate = ''
    eptitle = ''
    for epdate, eplink, epname in matches:
        item = episode_makeitem(epname, eplink, epdate)
        item.set_path(plugin.url_for(episode, name=epname, url=eplink))
        dateout = epdate.replace(' ', '-').strip()
        item.label += " [I][B][COLOR orange]{0}[/COLOR][/B][/I]".format(dateout)
        litems.append(item)
    plugin.notify(msg="Search {0}".format(urlsearch), title="{0} {1}".format(str(len(litems)), searchquery))
    return litems


@plugin.route('/queryshow/<searchquery>')
def queryshow(searchquery):
    plugin.clear_added_items()
    plugin.add_items(items=query(searchquery))
    return plugin.finish(update_listing=True)  # plugin.redirect(url=plugin.url_for(query, searchquery=searchquery))
    # resitems = query(searchquery)
    # return plugin.finish(items=resitems, succeeded=True, update_listing=True)
    # return plugin.add_items(resitems)


@plugin.route('/category/<name>/<url>')
def category(name='', url=''):
    html = ''
    if not str(url).startswith('http'):
        url = __BASEURL__ + '/' + url
    html = DL(url)
    banner = 'DefaultVideoFolder.png'
    epre = re.compile(ur'href="(https?://www?1?\.watchseries-online.[a-z]+/episode/.+?)" .+?<span.+?</span>(.+?)</a>')
    matches = epre.findall(html)
    litems = []
    if len(matches) > 1000: matches = matches[0:1000]
    for eplink, epname in matches:
        itempath = plugin.url_for(endpoint=episode, name=epname, url=eplink)
        #item = ListItem(label=epname, label2=eplink, icon='DefaultVideo.png', thumbnail='DefaultVideo.png',path=itempath)
        item = episode_makeitem(epname, eplink)
        litems.append(item)
        #plugin.log.info(msg="** {0}\t{1}".format(epname, eplink))
    plugin.notify(msg="Category {0}".format(name), title=str(len(litems)))
    if plugin.get_setting(key='sortalpha', converter=bool):
        litems.sort(key=lambda litems: litems.label, reverse=True)
    return litems


@plugin.route('/episode/<name>/<url>')
def episode(name='', url=''):
    waserror = False
    linklist = []
    if len(url) == '':
        waserror = True
    else:
        html = DL(url)
        litems = []
        linklist = findvidlinks(html)
        itemparent = None
    if len(linklist) > 0:
        for name, link in linklist:
            itempath = plugin.url_for(play, url=link)
            item = dict(label=name, label2=link, icon='DefaultFolder.png', thumbnail='DefaultFolder.png', path=itempath)
            item.setdefault(item.keys()[0])
            litems.append(item)
        vitems = sortSourceItems(litems)
        litems = []
        for li in vitems:
            item = ListItem.from_dict(**li)
            item.set_is_playable(True)
            item.set_info(info_type='video', info_labels={'Title': item.label, 'Plot': item.label2})
            item.add_stream_info(stream_type='video', stream_values={})
            litems.append(item)
    else:
        waserror = True
    if waserror:
        plugin.notify(title="ERROR No links: {0}".format(name), msg=url)
        return []
    return litems


@plugin.route('/playfirst/<url>')
def playfirst(url=''):
    idx = 0
    if len(url) < 1:
        return None
    html = DL(url)
    prefhost = ''
    sourceslist = []
    blockedlist = []
    stext = plugin.get_setting('topSources')
    btext = plugin.get_setting('blockedSources')
    if len(stext) < 1:
        prefhost = 'vidoza'
    else:
        stext = stext.lower()
        stext = stext.strip(',')
        if stext.find(',') == -1:
            sourceslist.append(stext)
        else:
            sourceslist = stext.split(',')
        prefhost = sourceslist[0].lower()
    btext = plugin.get_setting('blockedSources')
    if len(btext) < 1:
       blockedlist.append('vshare')
    else:
        btext = btext.lower()
        btext = btext.strip(',')
        if btext.find(',') == -1:
            blockedlist.append(btext)
        else:
            blockedlist = btext.split(',')
    litems = []
    name = ''
    link = ''
    linklistall = []
    linklistall = findvidlinks(html, findhosts=sourceslist)
    if len(linklistall) > 0:
        for fitem in linklistall:
            lname,purl = fitem
            for source in blockedlist:
                lbl,hurl = source
                if purl.find(hurl) == -1:
                    linklist.append(fitem)
        if len(linklist) < 1: linklist = linklistall
        for fitem in linklist:
            vname,vurl = fitem
            for source in sourceslist:
                if vurl.find(source) != -1:
                    name = vname
                    link = vurl
                    break
                #foundhost = findahost(linklist, source)
                #if foundhost is not None:
                #    name, link = foundhost
                #    break
            if len(link) > 0:
                break
        if len(link) < 1:
            name, link = linklist[0]
    xbmc.log("Source {0} {1}".format(name, link))
    plugin.notify(msg="#{0} {1}".format(str(len(linklist)), sourceslist[:]), title=link)
    #if link.find('linkOut') != -1:
    #    urlout = link.split('?id=')[-1]
    #    link = base64.b64decode(urlout)
    return play(url=link.encode('utf-8', 'ignore'))
    '''
    #itempath = plugin.url_for(play, url=link)
    itempath = plugin.url_for(play, url=link)
    sitem = dict(label=name, label2=link, icon='DefaultFolder.png', thumbnail='DefaultFolder.png', path=itempath)
    sitem.setdefault(sitem.keys()[0])
    item = ListItem.from_dict(**sitem)
    item.set_is_playable(True)
    item.set_info(info_type='video', info_labels={'Title': item.label, 'Plot': item.label2})
    item.add_stream_info(stream_type='video', stream_values={})
    plugin.notify(msg=link, title=name)
    #plugin.add_items([item])
    item.set_played(was_played=True)
    #plugin.add_items([plugin.set_resolved_url(link)])#.as_tuple())])
    plugin.set_resolved_url(item)
    return plugin.play_video(item)
    #return [plugin.set_resolved_url(item)]
    #return [playurl(name=name, url=link)]
    # return plugin.finish(items=[plugin.set_resolved_url(item=play(link))])
    '''


def findahost(linklist=[], prefhost=""):
    for fitem in linklist:
        lb, vu = fitem
        xbmc.log("Lookin for host: {0} in {1}".format(prefhost, vu))
        vu = vu.lower()
        if vu.find(prefhost) != -1:
            return (lb,vu,)
    return None


@plugin.route('/resolveurl')
def resolveurl():
    playable = None
    resolved = ""
    url = plugin.keyboard(default='', heading='Video Page URL')
    if url is not None:
        name = url
        if len(url) > 0:
            url = url.encode('utf-8', 'ignore')
            item = ListItem(label=name, label2=url, icon='DefaultVideo.png', thumbnail='DefaultVideo.png', path=plugin.url_for(endpoint=play, url=url))
            item.playable = True
            item.set_info(info_type='video', info_labels={'Title': url, 'Plot': url})
            item.add_stream_info(stream_type='video', stream_values={})
            playable = play(url)

            try:
                resolved = urlresolver.resolve(url)
            except:
                resolved = ""
            plugin.notify(msg=resolved, title="Playing..")
            return plugin.play_video(playable)
    #plugin.redirect(plugin.url_for(index))
    #plugin.clear_added_items()
    #plugin.end_of_directory()
    #return None
    return None


@plugin.route('/play/<url>')
def play(url):
    if url.find('linkOut') != -1:
        urlout = url.split('?id=')[-1]
        url = base64.b64decode(urlout)
    resolved = ''
    stream_url = ''
    item = None
    try:
        if urlresolver is not None:
            stream_url = urlresolver.resolve(url)
        if len(stream_url) > 1:
            resolved = stream_url
    except:
        plugin.notify(msg="{0}".format(url), title="URLResolver FAILED", delay=1000)
    if len(resolved) < 1:
        plugin.notify(msg="{0}".format(url), title="Trying YouTube-DL", delay=1000)
        try:
            import YDStreamExtractor
            info = YDStreamExtractor.getVideoInfo(url, resolve_redirects=True)
            stream_url = info.streamURL()
            if len(stream_url) < 1 or stream_url.find('http') == -1:
                for s in info.streams():
                    try:
                        stream_url = s['xbmc_url'].encode('utf-8', 'ignore')
                        xbmc.log(msg="**YOUTUBE-DL Stream found: {0}".format(stream_url))
                    except:
                        pass
                if len(stream_url) > 1:
                    resolved = stream_url
            else:
                resolved = stream_url
        except:
            plugin.notify(msg="{0}".format(url), title="YOUTUBE-DL Failed", delay=1000)
    if len(resolved) < 1:
        plugin.notify(msg="{0}".format(url), title="FAILED TO RESOLVE", delay=1000)
        return None
    else:
        vidurl = resolved.encode('utf-8', 'ignore')
        item = ListItem.from_dict(path=vidurl)
        item.add_stream_info('video', stream_values={})
        item.set_is_playable(True)
        plugin.set_resolved_url(item)
        return plugin.play_video(item)


@plugin.route('/playold/<url>')
def playold(url):
    if url.find('linkOut') != -1:
        urlout = url.split('?id=')[-1]
        url = base64.b64decode(urlout)
    resolved = ''
    stream_url = ''
    item = None
    try:
        if urlresolver is not None:
            resolved = urlresolver.resolve(url)
        if len(resolved) > 1:
            plugin.notify(msg="PLAY {0}".format(resolved.split('://',1)[-1]), title="URLRESOLVER", delay=1000)
            plugin.set_resolved_url(resolved)
            item = ListItem.from_dict(path=resolved)
            item.add_stream_info('video', stream_values={})
            item.set_is_playable(True)
            plugin.play_video(item)
            return None
    except:
        resolved = ''
        plugin.notify(msg="FAILED {0}".format(url), title="URLResolver", delay=1000)
    try:
        import YDStreamExtractor
        info = YDStreamExtractor.getVideoInfo(url, resolve_redirects=True)
        resolved = info.streamURL()
        for s in info.streams():
            try:
                stream_url = s['xbmc_url'].encode('utf-8', 'ignore')
                xbmc.log(msg="**YOUTUBE-DL Stream found: {0}".format(stream_url))
            except:
                pass
        if len(stream_url) > 1:
            resolved = stream_url
        if len(resolved) > 1:
            plugin.notify(msg="PLAY: {0}".format(resolved.split('://', 1)[-1]), title="YOUTUBE-DL", delay=1000)
            plugin.set_resolved_url(resolved)
            item = ListItem.from_dict(path=resolved)
            item.add_stream_info('video', stream_values={})
            item.set_is_playable(True)
            plugin.play_video(item)
            return None
    except:
        plugin.notify(msg="Failed: {0}".format(resolved.partition('.')[-1]), title="YOUTUBE-DL", delay=1000)
    if len(resolved) > 1:
        plugin.set_resolved_url(resolved)
        item = ListItem.from_dict(path=resolved)
        plugin.play_video(item)
        return None
    else:
        plugin.set_resolved_url(url)
        plugin.play_video(url)
        return None


if __name__ == '__main__':
    hostname = ''
    hostname = plugin.get_setting('setHostname')
    if len(hostname) > 1:
        hostname = hostname.strip()
        hostname = hostname.strip('/')
        if str(hostname).startswith('http'):
            __BASEURL__ = hostname
        else:
            __BASEURL__ = 'https://' + hostname
    plugin.run()
    plugin.set_content('episodes')
    plugin.set_view_mode(0)
