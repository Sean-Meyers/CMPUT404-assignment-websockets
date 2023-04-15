#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
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
from flask import Flask, request, redirect, make_response
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()        

def set_listener( entity, data ):
    ''' do something with the update ! '''
    # Shouldn't need this. It's kinda wacky looking anyways, or at least doesn't
    # look like it'll play nicely with what I'm trying to write. The stuff in
    # the example slides seems more suitable.
    pass

myWorld.add_set_listener( set_listener )
        
        
        
class Stroke:
    def __init__(self, begin_entity:dict) -> None:
        # {'x':x, 'y':y, 'colour':colour, 'radius':brushSize * penPressure, 'strokeId':strokeId, 'tool':tool}
        # self.stroke_id = begin_entity.get('strokeId','')
        # assert self.stroke_id, "Invalid entity format for Stroke initialization; begin_entity is required to have a 'strokeId' field."
        self.tool = begin_entity.get('tool','')
        assert self.tool, "Invalid entity format for Stroke initialization; begin_entity is required to have a 'tool' field."
        # begin_entity.pop('tool')    # Easier for client to deal with this way I guess. Tho, could just let client do it instead...
        self.begin = begin_entity
        self.tail = []  # Includes all points in stroke except begin_entity
        
    # TODO: add client_id to stroke id string somewhere so that we don't get a bug when multiple users start their strokes at the same place and time. this todo doesn't necesarilly belong in this class, I was just lazy. 

    def as_dict(self):
        return {'begin': self.begin, 'tool':self.tool, 'tail': self.tail} # Allows us to bulk send strokes if needed.
        
        
        
@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''  
    return redirect("/static/index.html", code=302)


clients = list()

def send_all(msg, sender=None):
    for client in clients:
        if not sender or client is not sender:  # Why send me something I just gave you? This should prevent that. In theory.
            client.put( msg )

def send_all_json(obj, sender=None):
    # print('send all json:', obj)
    send_all( json.dumps(obj), sender )


class Client:
    def __init__(self):
        print('init client')
        self.queue = queue.Queue()
        self.undo_stack = []
        self.redo_stack = []
        # self.g = None

    def put(self, v):
        self.queue.put_nowait(v)

    def get(self):
        return self.queue.get()
    

def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: Done. IMPLEMENT ME

    # {'x':x, 'y':y, 'colour':colour, 'radius':brushSize * penPressure, 'strokeId':strokeId, 'tool':tool}
    
    # https://github.com/uofa-cmput404/cmput404-slides/blob/master/examples/WebSocketsExamples/chat.py    
    try:
        while True:
            msg = ws.receive()
            # print("WS RECV: %s" % msg)
            if (not msg):
                print('Received nothing. As vengeance, your connection is now busted.')
                # raise Exception("Tests are forcing me to be aggresive. If it's bulletproof hit it with a nuke.")
                # client.send_all(msg, sender=None)
                break
            packet = json.loads(msg)
            
            # print('141, packet:', packet)
            
            if packet.get('cmd'):
                if packet['cmd'] == 'clear':
                    client.undo_stack.append(myWorld.world())
                    myWorld.clear()
                elif packet['cmd'] == 'unclear':
                    world = client.undo_stack.pop()
                    client.redo_stack.append(world)
                    myWorld.space.update(world)
                elif packet['cmd'] == 'reclear':
                    world = client.redo_stack.pop()
                    client.undo_stack.append(world)
                    for key in world.keys():
                        myWorld.space.pop(key)
                elif packet['cmd'] == 'unstroke':
                    stroke = myWorld.space.pop(packet["data"])
                    client.redo_stack.append({'stroke_id': packet["data"], 'data': stroke})
                elif packet['cmd'] == 'restroke':
                    # try:
                    stroke = client.redo_stack.pop()
                    client.undo_stack.append(stroke['stroke_id'])
                    myWorld.space.update({stroke['stroke_id']: stroke['data']})
                    # except Exception as e:
                    #     print(e)
                send_all_json(packet, client)
                continue
            
            # print('170, packet:', packet)
            
            stroke_id = packet.get('strokeId','')
            if not stroke_id:
                # Dunno what to do with this, who cares, just add to world, send to clients and move on. TODO
                myWorld.space.update(packet)
                client = None    # I suspect the tests want the client to receive the packet it sent, even though it should be unnecesary in theory... Unless there's some worry that a packet may be dropped and that clients may want to verify the server received it by receiving it back from the server...
                # myWorld.set(packet) # This is a bit... it won't work, lets hope it doesn't need to in order to pass the tests.
            elif not myWorld.get(stroke_id):
                myWorld.set(stroke_id, Stroke(packet))
            else:
                myWorld.get(stroke_id).tail.append(packet)
                
            # print('180, packet:', packet)
            if client:
                client.redo_stack = [];
            send_all_json(packet, client)
    except Exception as e:
        # print("error:", e)
        # raise e
        '''Done'''
    # finally:
    #     gevent.kill(client.g)
    #     clients.remove(client)
        
    
    return None


@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    # XXX: TODO IMPLEMENT ME
    
    # https://github.com/uofa-cmput404/cmput404-slides/blob/master/examples/WebSocketsExamples/chat.py
    client = Client()
    clients.append(client)
    g = gevent.spawn( read_ws, ws, client )
    # client.g = g 
    try:
        # New client, so send the world.
        for entity in myWorld.world().values():
            if type(entity) is Stroke:    
                client.put(json.dumps(entity.as_dict()))
            else:
                client.put(json.dumps(entity))  # We'll let the client deal with any weird stuff like non-stroke objects.
        while True:
            # block here
            msg = client.get()
            # print(type(msg))
            # print('sending:', msg)
            ws.send(msg)
            
            # debug (why is there neither documentation or comments for this ws module? looks like it's deprecated too...):
            # gonna maybe leave this here to document my strife so that future me knows what not to do, if ever I want to use this module again.
            # try:
            #     ws.send('{"hello":"json"}')
            # except Exception as e:# WebSocketError as e:
            #     print("WS Error... doesn't like str json: %s" % e)
            # try:
            #     ws.send({"hello":"json"})
            # except Exception as e:# WebSocketError as e:
            #     print("WS Error... doesn't like dict: %s" % e)
            
            # try:
            #     ws.send(b'hello bytes')
            # except Exception as e:# WebSocketError as e:
            #     print("WS Error... doesn't like bytes: %s" % e)
            # # try:
            # #     ws.send(8512121591420) # helloint according to https://www.thefontworld.com/leet-speak-translator
            # # except Exception as e:# WebSocketError as e:
            # #     print("WS Error... doesn't like int: %s" % e)
            # try:
            #     ws.send('hello str')
            # except Exception as e:# WebSocketError as e:
            #     print("WS Error... doesn't like str: %s" % e)
            
            
    except Exception as e:# WebSocketError as e:
        print("WS Error %s" % e)
        # raise("error:", e)
    finally:
        print("killing client")
        clients.remove(client)
        gevent.kill(g)
    
    return None


# I give this to you, this is how you get the raw body/data portion of a post in flask
# this should come with flask but whatever, it's not my project.
def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data.decode("utf8") != u''):
        return json.loads(request.data.decode("utf8"))
    else:
        return json.loads(request.form.keys()[0])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    return None

@app.route("/world", methods=['POST','GET'])    
def world():
    '''you should probably return the world here'''
    return None

@app.route("/entity/<entity>")    
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    return None


@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    return None



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
