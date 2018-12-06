# encoding=utf8
import argparse, sys

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

# load from arguments

parser=argparse.ArgumentParser()

parser.add_argument('--week', '-w', help="The year you want to get, numbered", type= int)
parser.add_argument('--year', '-y', help="The year you want to get", type= int, default= 2018)
parser.add_argument('--limit', '-l', help="Amount of results", type= int, default= 25)
parser.add_argument('--thumbnailSize', '-ts', help="Size of thumbnail, in pixels", type= int, default= 80)
parser.add_argument('--outName', '-o', help="Name of the output file", type= str, default= 'weekly_data')
parser.add_argument('--format', '-f', help="formats, separated by comma. Possible: csv, json, wikicode", type= str, default= 'wikicode');
parser.add_argument('--stopwords', '-stop', help="stopwords, separated by comma", type= str, default= '')

args=parser.parse_args()
print args

#wikicode variables
w_year = args.year
w_week = args.week
w_limit = args.limit
w_thumbsize = args.thumbnailSize
w_croptemplate = 'Template:Ritaglio_immagine_con_CSS'
w_gnews_icon = 'Google_News_Logo.png'
w_stopwords = []#args.stopwords.split(',')
found_stopwords = []


# add saved stopwords
with open('assets/custom_stopwords.txt', 'r') as f:
	reader = csv.reader(f, delimiter='\t')
	for c in list(reader):
		w_stopwords.append(c[0])

print w_stopwords

#boolean variables to define the type of output
out_wikicode = False
out_json = False
out_csv = False
out_name = args.outName
if 'wikicode' in args.format:
	out_wikicode = True
if 'json' in args.format:
	out_json = True
if 'csv' in args.format:
	out_csv = True

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

	data = r.json()
	print 'getting image ' + title
	#get image license
	#get page id
	pageid = data['query']['pages'].keys()[0]

	license = 'none'

	#print json.dumps(data['query']['pages'][pageid], indent=4, sort_keys=True)
	try:
		img = {}
		img['thumbnail'] = data['query']['pages'][pageid]['thumbnail']['source']
		img['pageimage'] = data['query']['pages'][pageid]['pageimage']
		img['height'] = data['query']['pages'][pageid]['thumbnail']['height']
		img['width'] = data['query']['pages'][pageid]['thumbnail']['width']
		img['pageimage'] = data['query']['pages'][pageid]['pageimage']
		# now get the license
		img['license'] = getImageLicense(project, data['query']['pages'][pageid]['pageimage'])
		print '\t',img['license']['licenseShortName']

		return img
	except Exception,e: print '\t[image error]',str(e)

def getImageLicense(project, title):
	#https://en.wikipedia.org/w/api.php?action=query&prop=imageinfo&iiprop=extmetadata&titles=File%3aBrad_Pitt_at_Incirlik2.jpg&format=json
	#https://commons.wikimedia.org/w/api.php?action=query&prop=imageinfo&iiprop=extmetadata&titles=File:Lorenzo_de_Medici.jpg&format=json
	baseurl = 'https://' + project + '.org/w/api.php'
	params = {}
	params['action'] = 'query'
	params['prop'] = 'imageinfo'
	params['iiprop'] = 'extmetadata'
	params['titles'] = 'File:'+title
	params['format'] = 'json'

	r = requests.get(baseurl, params = params)
	#print params['titles']
	data = r.json()
	print 'getting license for ' + title
	#print r.url

	#get page id
	pageid = data['query']['pages'].keys()[0]

	try:
		results = {}
		#results['license'] = data['query']['pages'][pageid]['imageinfo'][0]['extmetadata']['License']['value']
		results['licenseShortName'] = data['query']['pages'][pageid]['imageinfo'][0]['extmetadata']['LicenseShortName']['value']
		results['copyrighted'] = data['query']['pages'][pageid]['imageinfo'][0]['extmetadata']['Copyrighted']['value']
		return results
	except Exception,e: print '\t[license error]',str(e)

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
	except Exception,e:
		print '[snippet error]',str(e)
		return ''

# function to set category
def setCategory(title):
	#results
	result = ''
	#load categories
	categories = {}
	with open('assets/categories.csv', 'r') as f:
		reader = csv.reader(f, delimiter='\t')
		for c in list(reader):
			categories[c[0]] = c[1]

	#load previously categorized pages
	categorized = {}
	with open('assets/categorized.csv', 'r') as f:
		reader = csv.reader(f, delimiter='\t')
		for c in list(reader):
			categorized[c[0]] = c[1]
	#get pages names

	setNewCat = True
	#check if the title is already categorized
	if title in categorized:
		text =  'found ' + title + ' as ' + categorized[title] + ' do you want to keep it? [y/n]'
		if(raw_input(text) == 'y' or raw_input(text) == ''):
			setNewCat = False
			return categories[categorized[title]]


	if(setNewCat):
		#print all the possible values
		mx = 'Choose category for ' + title + '[' + ', '.join(categories) + ']: '
		text = ''
		#ask for imput
		while text not in categories:
			text = raw_input(mx)
			if text not in categories:
				print '\tnot a category: ', text
		# add the new categorization
		categorized[title] = text
		#save new cat
		with open('assets/categorized.csv', mode='w') as outFile:
			writer = csv.writer(outFile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
			for c in categorized:
				writer.writerow([c, categorized[c]])
		#return the associate code
		return categories[text]

# generic function to sum statistics of multiple days.
#
# project: in which language you want the page. Two-letters codes (it, en, pt, es, ...)
# startdate: starting date, as datetime object.
# enddate: ending date, as datetime object.
# limit: maximum amount of pages you want to get. Max: 1000. Default: 1000.
# thumbsize: target size of the thumbnail. Default: 1000.

def getSum(project,startdate,enddate,limit=1000, thumbsize=1000):

	#define stopwords
	stopwords = ['Progetto:','Pagina_principale','Wikipedia:','Aiuto:','Speciale:','Special:','File:','Categoria:','load.php']
	#add the custom ones
	#stopwords = stopwords + w_stopwords

	print stopwords
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
		if elm[0] in w_stopwords:
			stop = True
			found_stopwords.append(elm[0].replace('_',' '))
			print '\tfound custom sw: '+elm[0]
		if not stop:
			obj = {}
			obj['title'] = elm[0]
			obj['pageviews'] = elm[1]
			obj['rank'] = rank
			articles.append(obj)
			rank = rank + 1

	#add imgs and snippet
	for article in articles[:limit]:
		article['image'] = getImage('it.wikipedia', article['title'], thumbsize)
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
		#print json.dumps(raw_stats, indent=4, sort_keys=True) # check from here error of 6 output
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

#save wikicode
if out_wikicode == True:

	#get data
	query = getWeekList('it.wikipedia', w_year, w_week-1, w_limit, None)

	#initialize the page
	wikicode = '{{Utente:Mikima/Top25/Template:Anni|settimana='+str(w_week)+'}}\n\n'

	wikicode += '← [[Utente:Mikima/Top25/' + str(w_year) + '-' + str(w_week-1) + '|Settimana precedente]] – [[Utente:Mikima/Top25/' + str(w_year) + '-' + str(w_week+1) + '|Settimana successiva]] →\n\n'
	# create the string
	italianMonths = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
	# decode dates
	date_st = datetime.strptime(query['startdate'],"%Y-%m-%d")
	date_ed = datetime.strptime(query['enddate'],"%Y-%m-%d")
	# encode dates
	st_day = int(date_st.strftime("%e"))
	ed_day = int(date_ed.strftime("%e"))
	st_month = italianMonths[int(date_st.strftime("%m"))-1]
	ed_month = italianMonths[int(date_ed.strftime("%m"))-1]
	st_year = date_st.strftime("%Y")
	ed_year = date_ed.strftime("%Y")
	if ( st_month == ed_month):
		#same month
 		wikicode += 'Settimana dal ' + str(st_day) + ' al ' + str(ed_day) + ' ' + ed_month + ' ' + ed_year + '\n\n'
	else:
		#different month
		wikicode += 'Settimana dal ' + str(st_day) + ' ' + st_month + ' al ' + str(ed_day) + ' ' + ed_month + ' ' + ed_year + '\n\n'
	# add filtered pages
	#create table
	wikicode += '{| class="wikitable sortable"\n!Posizione\n!Articolo\n!News\n!Giornaliero\n!Visite\n!Immagine\n!Descrizione\n'
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

		image = ''

		if item['image'] is not None:
			#print item['image']['license']['licenseShortName']
			if item['image']['license']['licenseShortName'] != 'Copyrighted' and item['image']['license']['licenseShortName'] != 'Marchio':
				print '\t license accettable:', item['image']['license']['licenseShortName']
				try:
					#print item['image']['pageimage'], item['image']['width'], item['image']['height']
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
						#print 'bsize: ', bsize, ' oleft: ', oleft

					#prepare code for image
					image = '{{' + w_croptemplate + '|oLeft = ' +str(oleft)+ '|oTop = ' + str(otop) + '|bSize = ' + str(bsize) + '|cWidth = ' + str(w_thumbsize) + '|cHeight = ' + str(w_thumbsize) + '|Image = ' + item['image']['pageimage'] + '}}'
				except Exception as e:
					print '\t[thumb creation error]',str(e)

		if image == '':
			#since no image is available, use categories
			image = setCategory(item['title'])

		wikicode += '|-\n!'+ rank + '\n|[['+ title +']]\n|'+ google_news +'\n|'+ w_chart + '\n\n' + wmf_tools +'\n|'+ pageviews +'\n|'+ image +'\n|'+snippet+'\n'

	#close table
	wikicode += '|}'
	#add filtered
	wikicode += 'Pagine filtrate: [[' + ']], [['.join(found_stopwords) + ']]\n\n'

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
