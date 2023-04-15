#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2023 Abram Hindle, Sean Meyers
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, redirect
from flask_sockets import Sockets
import gevent
from gevent import queue
import json

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True



class World:
    '''Za Warudo'''
    
    def __init__(self):
        self.clear()

    def set(self, entity, data):
        self.space[entity] = data

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity, dict())
    
    def world(self):
        return self.space
    

class Stroke:
    '''
    Represents all the context and data captured since the user touches the
    screen, up to and including when they stop touching the screen.
    
    A stroke may be incomplete, such as when it is sent to us while the user is
    still drawing so that other's can see it in real time.
    '''
    def __init__(self, begin_entity:dict) -> None:
        # {'x':x, 'y':y, 'colour':colour, 'radius':brushSize * penPressure, 'strokeId':strokeId, 'tool':tool}
        
        self.tool = begin_entity.get('tool','')
        assert self.tool, "Invalid entity format for Stroke initialization; begin_entity is required to have a 'tool' field."
        
        self.begin = begin_entity
        self.tail = []  # Includes all points in stroke except begin_entity

    def as_dict(self):
        '''
        Return a dict representation of the Stroke.
        Allows us to bulk send strokes if needed.
        '''
        return {'begin': self.begin, 'tool':self.tool, 'tail': self.tail}
    
    
    
class Client:
    '''
    Holds stuff until we're ready to send it to the client.
    
    Shamelessly ripped from Abram's chat.py:
    https://github.com/uofa-cmput404/cmput404-slides/blob/master/examples/WebSocketsExamples/chat.py
    '''
    def __init__(self):
        self.queue = queue.Queue()
        self.undo_stack = []
        self.redo_stack = []

    def put(self, v):
        self.queue.put_nowait(v)

    def get(self):
        return self.queue.get()



myWorld = World()
clients = list()   
        
        
def send_all(msg, sender=None):
    for client in clients:
        # Why send me something I just gave you? This prevents that.
        if not sender or client is not sender:
            client.put(msg)

def send_all_json(obj, sender=None):
    send_all(json.dumps(obj), sender)
    
    
@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''  
    return redirect("/static/index.html", code=302)


def handle_command(json_packet:dict, client:Client, command:str):
    '''
    Do server magic when the client presses undo/redo/clear
    '''
    if command == 'clear':
        client.undo_stack.append(myWorld.world())
        myWorld.clear()
        
    elif command == 'unclear':
        world = client.undo_stack.pop()
        client.redo_stack.append(world)
        myWorld.space.update(world)
        
    elif command == 'reclear':
        world = client.redo_stack.pop()
        client.undo_stack.append(world)
        for key in world.keys():
            myWorld.space.pop(key)
            
    elif command == 'unstroke':
        stroke = myWorld.space.pop(json_packet["data"])
        client.redo_stack.append({'stroke_id': json_packet["data"], 'data': stroke})
        
    elif command == 'restroke':
        stroke = client.redo_stack.pop()
        client.undo_stack.append(stroke['stroke_id'])
        myWorld.space.update({stroke['stroke_id']: stroke['data']})


def handle_stroke(stroke_id:str, json_packet:dict):
    '''
    Either add a new troke to the world, or append to it if it already exists.
    '''
    if not myWorld.get(stroke_id):
        myWorld.set(stroke_id, Stroke(json_packet))
    else:
        myWorld.get(stroke_id).tail.append(json_packet)


def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: Done. IMPLEMENTED
    
    # Format: {'x':x, 'y':y, 'colour':colour, 'radius':brushSize * penPressure, 'strokeId':strokeId, 'tool':tool}
    # Much WS stuff: Abram Hindle: https://github.com/uofa-cmput404/cmput404-slides/blob/master/examples/WebSocketsExamples/chat.py    
    try:
        # Try to receive messages from the client. Parse the message, decide what to do, do it.
        while True:
            msg = ws.receive()
            print("WS RECV: %s" % msg)
            
            if not msg:
                print('Received nothing. As vengeance, your connection is now busted (psych).')
                break
            
            # We could receive 3 different kinds of messages: a command to
            # undo/redo/clear, a stroke object representing a line on the
            # client's canvas, or misc data that we don't understand.
            packet = json.loads(msg)
            stroke_id = packet.get('strokeId','')
            command = packet.get('cmd', '')
            
            if command:
                handle_command(packet, client, command)
            elif stroke_id:
                handle_stroke(stroke_id, packet)
                client.redo_stack = [];
            else:
                myWorld.space.update(packet)
                client = None    # I suspect the tests want the client to receive the packet it sent, even though it should be unnecesary in theory... Unless there's some worry that a packet may be dropped and that clients may want to verify the server received it by receiving it back from the server...
                
            send_all_json(packet, client)
            
    except Exception:
        '''Done'''
    
    return None


@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''
    Fufill the websocket URL of /subscribe, every update notify the websocket
    and read updates from the websocket.
    ''' # XXX: Done. IMPLEMENTED
    
    # Much WS stuff: Abram Hindle: https://github.com/uofa-cmput404/cmput404-slides/blob/master/examples/WebSocketsExamples/chat.py
    client = Client()
    clients.append(client)
    g = gevent.spawn(read_ws, ws, client)
    try:
        # New client, so send the whole world.
        for entity in myWorld.world().values():
            if type(entity) is Stroke:    
                client.put(json.dumps(entity.as_dict()))
            else:
                # We'll let the client deal with any weird stuff like non-stroke objects.
                client.put(json.dumps(entity)) 
        
        # If the client has anything new in their queue, send it to them.
        while True:
            # block here
            msg = client.get()
            ws.send(msg)    # Note to self: ws.send doesn't like dicts and has terrible error messages, make sure to feed it strings.
            
    except Exception as e:# WebSocketError as e:
        print("WS Error %s" % e)
        
    finally:
        print("killing client")
        clients.remove(client)
        gevent.kill(g)
    
    return None




if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
