# encoding=utf8  
import sys  

reload(sys)  
sys.setdefaultencoding('utf8')

import pageviewapi
import requests
import json
import csv
import operator
import locale
import urllib
from datetime import datetime, timedelta, date


# Third version of the scaper.
# will output a TXT file with the final Wikicode.

# FUNCTIONS

# get date range function

def daterange(start_date, end_date):
	for n in range(int ((end_date - start_date).days + 1)):
		yield start_date + timedelta(n)

# get thumbnail image given the article name and the project.
# project: in which language you want the page. Two-letters codes (it, en, pt, es, ...)
# title: page title. Put the name with spaces or undescores.
# size: target size of the thumbnail.
#
# Example:
# https://it.wikipedia.org/w/api.php?action=query&titles=Silvio_Berlusconi&prop=pageimages&format=json&pithumbsize=1000

# to get copyright information, we can use a second query, like this:
# https://commons.wikimedia.org/w/api.php?action=query&titles=File:Silvio_Berlusconi_(2010)_cropped.jpg
#&prop=imageinfo
#&iiprop=extmetadata
#&format=json

# it should be rewrite using the V2 api:
# https://www.mediawiki.org/wiki/API:Page_info_in_search_results

def getImage(project, title, size):
	
	baseurl = 'https://'+project+'.org/w/api.php'
	params = {}
	params['action'] = 'query'
	params['titles'] = title
	params['prop'] = 'pageimages'
	params['format'] = 'json'
	params['pithumbsize'] = size
	
	r = requests.get(baseurl, params = params)
	#print params['titles']
	data = r.json()
	print 'getting image ' + title
	
	#get page id
	pageid = data['query']['pages'].keys()[0]
	#print json.dumps(data['query']['pages'][pageid], indent=4, sort_keys=True)
	try:
		img = {}
		img['thumbnail'] = data['query']['pages'][pageid]['thumbnail']['source']
		img['pageimage'] = data['query']['pages'][pageid]['pageimage']
		img['height'] = data['query']['pages'][pageid]['thumbnail']['height']
		img['width'] = data['query']['pages'][pageid]['thumbnail']['width']
		img['pageimage'] = data['query']['pages'][pageid]['pageimage']
		# now get the license
		'''
		print ' getting license'
		print ' ', 'File:' + img['pageimage']
		
		baseurl2 = 'https://commons.wikimedia.org/w/api.php'
		params2 = {}
		params2['action'] = 'query'
		params2['titles'] = 'File:' + img['pageimage']
		params2['prop'] = 'imageinfo'
		params2['format'] = 'json'
		params2['iiprop'] = 'extmetadata'	
		r2 = requests.get(baseurl2, params = params2)
		
		data2 = r2.json()
		#print json.dumps(data2, indent=4, sort_keys=True)
		pageid2 = data2['query']['pages'].keys()[0]
		license = data2['query']['pages'][pageid2]['imageinfo'][0]['extmetadata']['LicenseShortName']
		'''
		
		return img
	except Exception,e: print str(e)

# get text snippet for a page
# https://www.mediawiki.org/wiki/API:Page_info_in_search_results
# https://it.wikipedia.org/w/api.php?action=query&formatversion=2&prop=pageterms&titles=Hunger%20Games%20(film)
def getSnippet(project, title):
	baseurl = 'https://'+project+'.org/w/api.php'
	params = {}
	params['action'] = 'query'
	params['formatversion'] = '2'
	params['titles'] = title
	params['prop'] = 'pageterms'
	params['format'] = 'json'
	
	r = requests.get(baseurl, params = params)
	data = r.json()
	print 'getting snippet ' + title
	#print json.dumps(data, indent=4, sort_keys=True)

	try:
		snippet = data['query']['pages'][0]['terms']['description'][0]
		return snippet
	except:
		return ''

# generic function to sum statistics of multiple days.
#
# project: in which language you want the page. Two-letters codes (it, en, pt, es, ...)
# startdate: starting date, as datetime object.
# enddate: ending date, as datetime object.
# limit: maximum amount of pages you want to get. Max: 1000. Default: 1000.
# thumbsize: target size of the thumbnail. Default: 1000.

def getSum(project,startdate,enddate,limit=1000, thumbsize=1000):
	
	#define stopwords
	stopwords = ['Progetto:','Pagina_principale','Wikipedia:','Aiuto:','Speciale:','Special:','File:','Categoria:','load.php','armi_segrete',"TeleColor", "TG_Norba_24"]
	
	#set up the maxvalue var
	
	maxvalue = 0

	data = dict()
	
	for date in daterange(startdate,enddate):
		print date.strftime("%Y-%m-%d")
		try:
			results = pageviewapi.top(project, date.year, date.strftime('%m'), date.strftime('%d'), access='all-access')
			#print json.dumps(results, indent=4, sort_keys=True)
			for item in results['items'][0]['articles']:
				if item['article'] in data:
					data[item['article']] += item['views']
				else:
					data[item['article']] = item['views']
		except:
			print('impossible to fetch ', date.strftime("%Y-%m-%d"))
		
	data = sorted(data.items(), key=operator.itemgetter(1), reverse=True)
	
	articles = []
	#create an object for each article
	rank = 1
	for elm in data:
		#chech stopwords
		stop = False
		for stopword in stopwords:
			if stopword in elm[0]:
				stop = True
				print 'stopped '+ elm[0]
				break
		if not stop:
			obj = {}
			obj['title'] = elm[0]
			obj['pageviews'] = elm[1]
			obj['rank'] = rank
			articles.append(obj)
			rank = rank + 1
	
	#add imgs and snippet
	for article in articles[:limit]:
		article['image'] = getImage(project, article['title'], thumbsize)
		article['snippet'] = getSnippet(project, article['title'])
	
	#add pageviews
	for article in articles[:limit]:
		print 'loading stats for', article['title'], ' from ', startdate.strftime('%Y%m%d'), ' to ', enddate.strftime('%Y%m%d')
		raw_stats = pageviewapi.per_article(project, urllib.quote(article['title'].encode('utf8')), startdate.strftime('%Y%m%d'), enddate.strftime('%Y%m%d'), access='all-access', agent='all-agents', granularity='daily')
		stats = []
		#parse raw stats
		#for now it is optimized for the vega code, quite messy.
		stats.append({})
		stats[0]['name'] = 'table'
		stats[0]['values'] = []
		print json.dumps(raw_stats, indent=4, sort_keys=True) # check from here error of 6 output
		for item in raw_stats['items']:
			item_result = {}
			item_result['x'] = datetime.strptime(item['timestamp'],"%Y%m%d%M").strftime("%m/%d/%Y")
			item_result['y'] = item['views']
			if int(item['views']) > maxvalue:
				maxvalue = int(item['views'])
			
			stats[0]['values'].append(item_result)
			
		print json.dumps(stats, indent=4, sort_keys=True) # check from here error of 6 output
		article['stats'] = stats
	
	results = {}
	results['maxvalue'] = maxvalue
	results['project'] = project
	results['startdate'] = startdate.strftime("%Y-%m-%d")
	results['enddate'] = enddate.strftime("%Y-%m-%d")
	results['articles'] = articles[:limit]
	
	return results
	
# function to get the sum for a specific week (monday-sunday).
#
# project: in which language you want the page. Two-letters codes (it, en, pt, es, ...)
# year: target year, as four-digit number.
# week: week number (from 0 to 51).
# limit: maximum amount of pages you want to get. Max: 1000. Default: 1000.
# thumbsize: target size of the thumbnail. Default: 1000.

def getWeekList(project, year, week,limit=1000,thumbsize=1000):
	startdate = datetime.strptime(str(year)+'-'+str(week)+'-0', '%Y-%W-%w') + timedelta(days=1)
	enddate = startdate + timedelta(days=6)
	
	results = getSum(project, startdate, enddate, limit, thumbsize)
	return results

#end of functions. main code below.

#wikicode variables
w_year = 2018
w_week = 20
w_limit = 25
w_croptemplate = 'Utente:Mikima/test/Template:CSS Crop'
w_gnews_icon = 'Google_News_Logo.png'
w_thumbsize = 80

#boolean variables to define the type of output
out_name = "weekly_data"
out_wikicode = True
out_json = True
out_csv = True

#save wikicode
if out_wikicode == True:
	
	#get data
	query = getWeekList('it.wikipedia', w_year, w_week-1, w_limit, None)
	
	#initialize the page
	wikicode = '{{Utente:Mikima/Top25/Template:Anni|settimana='+str(w_week)+'}}\r\r'
	
	wikicode += '← [[Utente:Mikima/Top25/' + str(w_year) + '-' + str(w_week-1) + '|Settimana precedente]] – [[Utente:Mikima/Top25/' + str(w_year) + '-' + str(w_week+1) + '|Settimana successiva]] →\r\r'
	
	wikicode += 'Settimana dal ' + query['startdate'] + ' al ' + query['enddate'] + '\r\r'
	
	#create table
	wikicode += '{| class="wikitable sortable"\r!Posizione\r!Articolo\r!News\r!Giornaliero\r!Visite\r!Immagine\r!Descrizione\r'
	for item in query['articles']:
		rank = str(item['rank'])
		title = item['title'].replace('_',' ')
		pageviews = "{:,}".format(item['pageviews']).replace(',','.')
		image = ''
		date_st = datetime.strptime(query['startdate'],"%Y-%m-%d")
		date_ed = datetime.strptime(query['enddate'],"%Y-%m-%d")
		proj = query['project']
		google_news = '[' + 'https://www.google.it/search?q=' + item['title'].encode('utf-8').replace("_","%20") + '&hl=it&gl=it&authuser=0&source=lnt&tbs=cdr:1,cd_min:' + date_st.strftime("%m/%d/%Y") + ',cd_max:' + date_ed.strftime("%m/%d/%Y") + '&tbm=nws' + ' ' + item['title'].encode('utf-8').replace("_"," ") +' su Google News]'
		wmf_tools = '[https://tools.wmflabs.org/pageviews/?project=' + proj + '.org&platform=all-access&agent=user&start=' + date_st.strftime("%Y-%m-%d") + '&end=' + date_ed.strftime("%Y-%m-%d") + '&pages=' + item['title'].encode('utf-8') + ' vedi dati]'
		w_chart = '<graph>{"width":100,"height":42,"padding":{"top":0,"left":0,"bottom":0,"right":0},"data":' + json.dumps(item['stats']) + ',"scales":[{"name":"x","type":"ordinal","range":"width","domain":{"data":"table","field":"x"}},{"name":"y","type":"linear","range":"height","domain":[0,' + str(query['maxvalue']) + '],"nice":true}],"marks":[{"type":"rect","from":{"data":"table"},"properties":{"enter":{"x":{"scale":"x","field":"x"},"width":{"scale":"x","band":true,"offset":-0.5},"y":{"scale":"y","field":"y"},"y2":{"scale":"y","value":0}},"update":{"fill":{"value":"steelblue"}},"hover":{"fill":{"value":"red"}}}}]}</graph>'
		snippet = ''
		if item['snippet'] != '':
			snippet = "''"+item['snippet']+"'' (descrizione automatica)"
		
		try:
			print item['image']['pageimage'], item['image']['width'], item['image']['height']
			bsize = 0
			oleft = 0
			otop = 0
			
			#check which side is bigger
			if item['image']['height'] > item['image']['width'] :
				bsize = w_thumbsize
				hsize = int((item['image']['height']+ 0.0) / (item['image']['width'] + 0.0) * w_thumbsize)
				otop = int((hsize - w_thumbsize)/2)
			else:
				
				bsize = int((item['image']['width']+ 0.0) / (item['image']['height'] + 0.0) * w_thumbsize)
				oleft = int((bsize - w_thumbsize)/2)
				print 'bsize: ', bsize, ' oleft: ', oleft
			
			#prepare code for image
			image = '{{' + w_croptemplate + '|oLeft = ' +str(oleft)+ '|oTop = ' + str(otop) + '|bSize = ' + str(bsize) + '|cWidth = ' + str(w_thumbsize) + '|cHeight = ' + str(w_thumbsize) + '|Image = ' + item['image']['pageimage'] + '}}'
		except Exception as e:
			image = ''
			print str(e)
		
		wikicode += '|-\r!'+ rank + '\r|[['+ title +']]\r|'+ google_news +'\r|'+ w_chart + '\r\r' + wmf_tools +'\r|'+ pageviews +'\r|'+ image +'\r|'+snippet+'\r'
	
	#close table
	wikicode += '|}'
	
	#save txt
	text_file = open(out_name + ".txt", "w")
	text_file.write(wikicode.encode('utf8'))
	text_file.close()
	
#save json and csv file

if out_json == True | out_csv == True:
	
	#variables
	jsonobj = {}
	jsonobj['results'] = []
	
	#get data
	query = getWeekList('it.wikipedia', w_year, w_week-1, w_limit)
	query['week_number'] = w_week
	jsonobj['results'].append(query)


	#print json.dumps(jsonobj, indent=4, sort_keys=True)
	if out_json == True:
		with open(out_name + '.json', 'w') as outfile:
			json.dump(jsonobj, outfile)

	# Save CSV
	if out_csv == True:
		#create csv file
		ofile  = open(out_name + '.csv', "wb")
		writer = csv.writer(ofile, delimiter='\t', quotechar='"')
		writer.writerow(['Start Date','End Date','Rank','Image','Link', 'Title', 'Google News', 'WMF tools','Pageviews'])

		for item in jsonobj['results']:
	
			date_st = datetime.strptime(item['startdate'],"%Y-%m-%d")
			date_ed = datetime.strptime(item['enddate'],"%Y-%m-%d")
			print date_st, date_ed
			proj = item['project']
			for article in item['articles']:
				print article
				link = "https://" + proj + ".org/wiki/" + article['title']
				imgurl = ''
				try:
					imgurl = article['image']['thumbnail']
				except:
					imgurl = ''
			
				google_news = 'https://www.google.it/search?q=' + article['title'].encode('utf-8').replace("_"," ") + '&hl=it&gl=it&authuser=0&source=lnt&tbs=cdr:1,cd_min:' + date_st.strftime("%m/%d/%Y") + ',cd_max:' + date_ed.strftime("%m/%d/%Y") + '&tbm=nws'
				wmf_tools = 'https://tools.wmflabs.org/pageviews/?project=' + proj + '.org&platform=all-access&agent=user&start=' + date_st.strftime("%Y-%m-%d") + '&end=' + date_ed.strftime("%Y-%m-%d") + '&pages=' + article['title'].encode('utf-8')
				writer.writerow([item['startdate'],item['enddate'], article['rank'] , imgurl, link.encode('utf-8'), article['title'].encode('utf-8').replace("_"," "), google_news, wmf_tools, article['pageviews']])
