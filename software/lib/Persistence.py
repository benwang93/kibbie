"""
Library to provide persistence methods for classes

A python class can create a persistence object and read/update values

Each persistence object is identified by an ID. Any persistence objects created with the ID will share the same datastore.

"""

import os
import json

PERSISTENCE_FOLDER = "persistence"

class Persistence:
    def __init__(self, id):
        self.id = id
        self.filepath = os.path.join(PERSISTENCE_FOLDER, id + ".json")

        # The main dictionary for this persistence object
        self.data = {}

        # Create persistence folder if needed
        os.makedirs(PERSISTENCE_FOLDER, exist_ok=True)

        # Attempt to load previous state if it exists
        if os.path.exists(self.filepath):
            # Attempt to open and load CSV to a dictionary
            try:
                with open(self.filepath, 'r') as fin:
                    self.data = json.load(fin)
            except:
                print(f"Failed to load persistence json {self.filepath}")

    def persist(self):
        with open(self.filepath, 'w') as fout:
            fout.write(json.dumps(self.data))
    
    def get(self, key):
        key_str = str(key)
        if key_str in self.data:
            return self.data[key_str]
        else:
            return None
    
    def set(self, key, value):
        key_str = str(key)
        self.data[key_str] = value

        # Persist to file
        self.persist()
    
    # Use this method if updating a lot of fields at once, then call persist afterwards
    def setWithoutPersist(self, key, value):
        self.data[key] = value