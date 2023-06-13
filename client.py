import websocket
from time import sleep, time
from random import randint
from _thread import start_new_thread
import requests
from json import loads, dumps
from color import color
import os

TOKEN = os.environ["TOKEN"]
MY_LIB = "CustomImpl"
INTENTS = 512 # message events

heartbeat_interval = 0
sequence = None
running = True
jitter = True
identify_state = False
socket = None

def fetch_json(url):
	return loads(requests.get(url, headers={"Authorization": "Bot " + TOKEN }).content.decode())

def get_ws_url():
	gateway_url = fetch_json("https://discord.com/api/gateway/bot")["url"]
	return gateway_url + "?v=9&encoding=json" # compression is off for now

def create_heartbeat_packet():
	heartbeat_packet = {
		"op": 1,
		"d": None
	}
	if not sequence == None:
		heartbeat_packet["d"] = sequence

	return heartbeat_packet

def send_heartbeat(ws):
	global running

	packet = create_heartbeat_packet()
	ws.send(dumps(packet))

def heartbeat_sender(ws):
	global jitter

	print(f"{color.YELLOW}> Started heartbeat sender{color.ENDC}")
	print(f"{color.BLUE}heartbeat interval is {heartbeat_interval}{color.ENDC}")
	if jitter:
		jit = randint(0, 1)
		jitter = False
		sleep(heartbeat_interval * jit)
	while running:
		print(f"{color.GREEN}>> Sent heartbeat!{color.ENDC}")
		send_heartbeat(ws)
		sleep(heartbeat_interval) 

def send_identify(ws):
	print(f"{color.YELLOW}>> Sending identify packet...{color.ENDC}")
	packet = {
		"op": 2,
		"d": {
			"token": TOKEN,
			"intents": INTENTS,
			"properties": {
				"$os": "linux",
				"$browser": MY_LIB,
				"$device": MY_LIB
			}
		}
	}
	ws.send(dumps(packet))

def send_status(value, ws):
	print(f"{color.YELLOW}>> Sending status packet{color.ENDC}")
	packet = {
  		"op": 3,
  		"d": {
    			"since": time(),
    			"activities": [{
      				"name": value,
      				"type": 0
    			}],
    			"status": "online",
    			"afk": False
  		}
	}
	ws.send(dumps(packet))

def open_handler(ws):
	global socket

	socket = ws
	print(f"{color.YELLOW}> Websocket connected{color.ENDC}")

def msg_handler(ws, msg):
	global heartbeat_interval
	global identify_state

	packet = loads(msg)
	op_code = packet["op"]
	"""
		op codes:
			10 - heart beat interval, cache value
			1 - heart beat request, send heartbeat immedietly
	"""
	if op_code == 10:
		# heartbeating
		heartbeat_interval = int(packet["d"]["heartbeat_interval"]) / 1000
		start_new_thread(heartbeat_sender, (ws,))
		# identifying with the gateway
		send_identify(ws)
	elif op_code == 1:
		print(f"{color.RED}>> Server requested heartbeat{color.RED}")
		if "d" in packet:
			sequence = int(packet["d"])
		prev_beat_ack = False
		send_heartbeat(ws)
	elif op_code == 11:
		prev_beat_ack = True
		print(f"{color.GREEN}>> Server ACK heartbeat{color.ENDC}")
	elif op_code == 0:
		if packet["t"] == "READY":
			print(f"{color.GREEN}>> Received READY event (server ACK identify){color.ENDC}")
			identify_state = True
		elif packet["t"] == "MESSAGE_CREATE":
			print(f"{color.BLUE}>> Received MESSAGE_CREATE event{color.ENDC}")
			print(color.BLUE + packet["d"]["author"]["username"], "said", packet["d"]["content"] + color.ENDC)

def error_handler(ws, error):
	print(f"{color.RED}<!> Error: {str(error)}{color.ENDC}")

def close_handler(ws, status_code, close_msg):
	print(f"{color.RED}<!> Socket disconnected with status code {str(statuc_code)}, reason: {close_msg}{color.ENDC}")

def connect():
	ws = websocket.WebSocketApp(get_ws_url(), 
			on_open=open_handler, 
			on_message=msg_handler, 
			on_error=error_handler, 
			on_close=close_handler)
	ws.run_forever()

start_new_thread(connect, ())
while True:
	cmd = input("Command: ")
	value = input("Value: ")
	if socket == None:
		print(f"{color.RED}Socket is not initialized yet{color.ENDC}")
		continue
	if cmd == "status":
		send_status(value, socket)
