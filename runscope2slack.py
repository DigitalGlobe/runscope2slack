import requests, json
import time
import boto3
from slackclient import SlackClient
from PIL import Image, ImageDraw
import math
import os

runscope_apikey = os.environ.get('RUNSCOPE_APIKEY')
headers = {'Authorization':'Bearer '+runscope_apikey}
runscope_bucket = os.environ.get('RUNSCOPE_BUCKET')
slacktoken = os.environ.get('SLACK_TOKEN')
sc = SlackClient(slacktoken)

skiptitles = ['WF default domain 10 minute','WF t2medium domain 10 minute']

def run():

	# get list of all tests:
	url = 'https://api.runscope.com/buckets/%s/tests?count=30' % (runscope_bucket)
	r = requests.get(url,headers=headers)

	tests = [{'name': test['name'], 'id':test['id']} for test in r.json()['data']]

	# Get all metrics from runscope & average into daily & monthly uptimes
	time_periods = ['day','week','month']
	data = []
	for test in tests:
		if test['name'] in skiptitles:
			continue
		uptimes = []
		print 'getting uptimes for %s' % test['name'] + ' ' + test['id']
		for period in time_periods:
			url = 'https://api.runscope.com/buckets/%s/tests/%s/metrics?timeframe=%s' % (runscope_bucket, test['id'], period)
			r = requests.get(url,headers=headers)
			all_uptimes = [d['success_ratio'] for d in r.json()['response_times'] if d['success_ratio']]
			if len(all_uptimes) > 0:
				uptime = sum(all_uptimes) / len(all_uptimes)
			else:
				uptime = 0
			uptimes.append(uptime)
		data.append({'label':test['name'],'day': round(uptimes[0]*100,3), 'week': round(uptimes[1]*100,3), 'month': round(uptimes[2]*100,3)})



	# python imaging settings

	boxheight = 50
	boxwidth = 280
	num_columns = 3
	num_boxes = len(data)
	print num_boxes
	num_rows = int(math.ceil(float(num_boxes) / float(num_columns)))
	print num_rows

	image_height = num_rows * boxheight
	image_width = num_columns * boxwidth

	# python imaging constants
	GREEN = (10,200,10)
	RED = (200,55,55)
	BLACK = (0,0,0)
	red_threshold = 99.0  # turn stuff red if less than this many nines

	### Turn stats into an image:
	for period in time_periods:
		img = Image.new('RGB', (image_width, image_height), color = (255, 255, 255))
		d = ImageDraw.Draw(img)
		r = 0
		c = 0
		for dat in data:
			print dat['label']
			print dat[period]
			if dat[period] < red_threshold:
				color = RED
			else:
				color = GREEN
			d.rectangle([c*boxwidth,r*boxheight,(1+c)*boxwidth,(1+r)*boxheight],fill=color, outline=BLACK)
			d.text((c*boxwidth+10,r*boxheight+10), dat['label'], fill=BLACK)
			d.text((c*boxwidth+50,r*boxheight+25), str(dat[period]), fill=BLACK)
			c = c + 1
			if c >= num_columns: 
				c = 0
				r = r + 1
			if r >= num_rows: r = 0

		img.save('/tmp/'+period + '.png')

		# upload image to s3
		s3key = period+'/' + str(time.time()) + '.png'
		s3 = boto3.resource('s3')
		imagedata = open('/tmp/'+period+'.png', 'rb')
		s3.Bucket('gbdx-service-uptime-images').put_object(Key=s3key, Body=imagedata)

		# push image to slack
		image_url = "https://s3.amazonaws.com/gbdx-service-uptime-images/" + s3key
		attachments = [{"title": "GBDX trailing " + period + " uptime", "image_url": image_url}]
		sc.api_call("chat.postMessage", channel='#gbdx-ops-daily', text='GBDX trailing '+period+' uptime',attachments=attachments)

if __name__=='__main__':
	run()

