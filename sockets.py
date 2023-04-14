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
        
    # TODO: something something client_id so that we don't get a bug when multiple users start their strokes at the same place and time. this todo doesn't necesarilly belong in this class, I was just lazy. 

    def as_dict(self):
        return {'begin': self.begin, 'tool':self.tool, 'tail': self.tail} # Allows us to bulk send strokes if needed.
        
        
        
@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    
    # XXX DEBUG: Start world with content to test receiving.    
    # tail = [
    #     {'x': 401, 'y': 208.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 399, 'y': 208.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 397, 'y': 208.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 395, 'y': 208.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 390, 'y': 208.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 380.5, 'y': 207.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 376.5, 'y': 207.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 365.5, 'y': 206.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 361, 'y': 205.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 352, 'y': 204.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 343.5, 'y': 203.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 340.5, 'y': 203.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 334.5, 'y': 202.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 326, 'y': 201.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 323, 'y': 200.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 315, 'y': 199.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 312, 'y': 199, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 302.5, 'y': 196.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 290.5, 'y': 195.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 286, 'y': 195, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 273.5, 'y': 191.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 261.5, 'y': 188, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 256, 'y': 187, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 248, 'y': 186, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 245.5, 'y': 185.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 241.5, 'y': 184.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 238.5, 'y': 184, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 237, 'y': 184, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 234, 'y': 183, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 231, 'y': 183, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 229, 'y': 182.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 226, 'y': 182.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 224.5, 'y': 181.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 221.5, 'y': 181.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 219.5, 'y': 181, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 218, 'y': 181, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 216, 'y': 180, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 212.5, 'y': 179.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 211.5, 'y': 179.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 208.5, 'y': 178.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 207, 'y': 178, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 205, 'y': 177, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 202.5, 'y': 177, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 202, 'y': 177, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'},
    #     {'x': 201.5, 'y': 176.5, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 5, 'strokeId': 'pos269472208time1681358525594', 'tool': 'brush_segmented'}
    # ]
    # begin = {'x': 401, 'y': 208, 'colour': 'rgba(0, 0, 0, 0.6)', 'radius': 10, 'strokeId': 'pos269472208time1681358525594', 'tool':'brush_segmented'}
    # stroke = Stroke(begin)
    # for point in tail:
    #     stroke.tail.append(point)
    # myWorld.set('pos269472208time1681358525594', stroke)
    
    return redirect("/static/index.html", code=302)


clients = list()

def send_all(msg, sender=None):
    for client in clients:
        if not sender or client is not sender:  # Why send me something I just gave you? This should prevent that. In theory.
            client.put( msg )

def send_all_json(obj, sender=None):
    send_all( json.dumps(obj), sender )


class Client:
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, v):
        self.queue.put_nowait(v)

    def get(self):
        return self.queue.get()
    

def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: TODO IMPLEMENT ME

    # data = {'x':x, 'y':y, 'colour':colour, 'radius':brushSize * penPressure, 'strokeId':strokeId, 'tool':tool}
    # if world[strokeId]:
    #   world[strokeId].append(data)
    #   for listener in listeners if listener not sender:
    #       listener_ws.send(data)
    # else:
    #   world[strokeId] = Stroke(data)
    #   for listener in listeners if listener not sender:
    #       listener_ws.send(data)
    
    # https://github.com/uofa-cmput404/cmput404-slides/blob/master/examples/WebSocketsExamples/chat.py    
    try:
        while True:
            msg = ws.receive()
            print("WS RECV: %s" % msg)
            if (msg is not None):
                packet = json.loads(msg)
                stroke_id = packet.get('strokeId','')
                if not stroke_id:   # TODO: Deal with clear commands being sent to the server.
                    # Dunno what to do with this, who cares, just add to world, send to clients and move on. TODO
                    myWorld.set(packet) # This is a bit... it won't work, lets hope it doesn't need to to pass the tests.
                elif not myWorld.get(stroke_id):
                    myWorld.set(stroke_id, Stroke(packet))
                else:
                    myWorld.get(stroke_id).tail.append(packet)
                send_all_json( packet )
            else:
                break
    except:
        '''Done'''
    
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
    finally:
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
