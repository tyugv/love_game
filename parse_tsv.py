import csv
import json


def parse_alphabet(alphabet_file):
    with open(alphabet_file, encoding='utf-8') as f:
        letters_tsv = list(csv.reader(f, delimiter='\t', quotechar='"'))[1:]

    letters_msgs = {}
    for letter in letters_tsv:
        if letter[0] == '':
            continue
        try:
            intent_id = letter[0]
            letters_msgs[intent_id] = {
                "text": letter[1].replace("'", '"').replace(' ENTER ', '\n'),
                "buttons": [],
                "intents": [],
                "sound": '',
                "image": letter[5]
            }
        except Exception as e:
            print(e)
            print(letter)

    return letters_msgs


def parse_dialogue(dialogue_file):
    with open(dialogue_file, encoding='utf-8') as f:
        dialogue_tsv = list(csv.reader(f, delimiter='\t', quotechar='"'))[1:]

    dialogue_msgs = {}

    for attributes in dialogue_tsv:
        if attributes[0] == '':
            continue
        try:
            id = int(attributes[0])
            dialogue_msgs[id] = {
                "text": attributes[1].replace("'", '"').replace(' ENTER ', '\n'),
                "buttons": [],
                "intents": [],
                "sound": attributes[4].replace("'", '"'),
                "image": attributes[5]
            }
            if attributes[2] != '':
                buttons = attributes[2].replace('True', '"True"').replace('False', '"False"').replace("'", '"') \
                    .replace('(', '[').replace(')', ']')
                for button in json.loads(buttons):
                    dialogue_msgs[id]["buttons"].append({
                        "text": button[0].replace('[', '(').replace(']', ')'),
                        "next_state": button[1],
                        "hide": button[2].lower() == "true"
                    })

            if attributes[3] != '':
                intents = attributes[3].replace("'", '"').replace('(', '[').replace(')', ']')
                for intent in json.loads(intents):
                    dialogue_msgs[id]["intents"].append({
                        "id": intent[0],
                        "next_state": intent[1],
                    })
        except Exception as e:
            print(e)
            print(attributes)

    return dialogue_msgs
