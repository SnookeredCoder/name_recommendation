import re
import os
from Levenshtein import *
import time
from pymongo import MongoClient
import pandas as pd
import psutil
client = MongoClient()
db = client['words']
collection = db['wordfrequency']



#Global Weights
soundex_wt = 0.2
bagging_wt = 0.1
surrounding_wt = 0.4
surrounding_miss_wt = 0.1
frequency_wt = 0.5

# Keyboard Visualization
keys = [['q','w','e','r','t','y','u','i','o','p'],
          ['a','s','d','f','g','h','j','k','l'],
            ['z','x','c','v','b','n','m']]


def find_distance(typed,suggested):
    all_distances = []
    if len(typed)!=len(suggested):
        return None
    for i in range(len(typed)):
        if typed[i]!=suggested[i]:
            typed_x , typed_y = get_key_index(typed[i])
            suggested_x, suggested_y = get_key_index(suggested[i])
            distance = abs(suggested_x-typed_x) + abs(suggested_y-typed_y)
            all_distances.append(distance)
    return all_distances


def get_score(typed,suggested,is_soundex=False,is_phonetic=False,is_bagging=False,is_surrounding=False):
    score = jaro_winkler(typed,suggested)
    if is_soundex:
        score += soundex_wt*(1-score)
    if is_phonetic:
        score = (1+score)/2.0
    if is_bagging:
        score += bagging_wt*(1-score)
    if is_surrounding:
        score += surrounding_wt*(1-score)
    else:
        if find_distance(typed,suggested):
            distances = find_distance(typed,suggested)
            if sum(distances)<4 and len(distances)<3:
                score += surrounding_miss_wt*(1-score)
    print(score)
    return score


# If Order is Changed like (Changes,Chagnes) 
def bagging_method(typed,suggested):
    typed_char = [i for i in typed]
    suggested_char = [i for i in suggested]
    if typed_char.sort()==suggested_char.sort():
        for i in range(1,len(typed)-1):
            current = typed[:i] + typed[i+1] + typed[i] + typed[i+2:]
            if current==suggested:
                return True
    return False


def generate_surrounding(char):
    surround = []
    char_x,char_y = get_key_index(char)
    if char_x==0:
        if char_y==0:
            surround.append(keys[char_x][char_y+1])
            surround.append(keys[char_x+1][char_y])
        elif char_y==9:
            surround.append(keys[char_x][char_y-1])
            surround.append(keys[char_x+1][char_y-1])
        else:
            surround.append(keys[char_x][char_y+1])
            surround.append(keys[char_x+1][char_y])
            surround.append(keys[char_x][char_y-1])
            surround.append(keys[char_x+1][char_y-1])
    elif char_x==1:
        if char_y==0:
            surround.append(keys[char_x][char_y+1])
            surround.append(keys[char_x-1][char_y])
            surround.append(keys[char_x-1][char_y+1])
            surround.append(keys[char_x+1][char_y])
        elif char_y==8:
            surround.append(keys[char_x-1][char_y])
            surround.append(keys[char_x-1][char_y+1])
            surround.append(keys[char_x][char_y-1])
        else:
            surround.append(keys[char_x-1][char_y])
            surround.append(keys[char_x-1][char_y+1])
            surround.append(keys[char_x][char_y+1])
            surround.append(keys[char_x][char_y-1])
            surround.append(keys[char_x+1][char_y-1])
            if char_y!=7:
                surround.append(keys[char_x+1][char_y])
    elif char_x==2:
        if char_y==0:
            surround.append(keys[char_x][char_y+1])
            surround.append(keys[char_x-1][char_y])
            surround.append(keys[char_x-1][char_y+1])
        elif char_y==6:
            surround.append(keys[char_x-1][char_y])
            surround.append(keys[char_x-1][char_y+1])
            surround.append(keys[char_x][char_y-1])
        else:
            surround.append(keys[char_x-1][char_y])
            surround.append(keys[char_x-1][char_y+1])
            surround.append(keys[char_x][char_y+1])
            surround.append(keys[char_x][char_y-1])
    return surround


def get_key_index(key_):
    row = -1
    col = -1
    for i in range(3):
        for j in range(len(keys[i])):
            if keys[i][j]==key_:
                row = i
                col = j
                return row,col
    return row, col


def find_keys_distance(key1,key2):
    key1_x,key1_y = get_key_index(key1)
    key2_x,key2_y = get_key_index(key2)

    print(key2_x-key1_x,key2_y-key1_y)
    return ""

# (3.5*n)
def check_surrounding(typed,suggested):
    for i in range(1,len(typed)):
        surrounds = generate_surrounding(typed[i])
        for surround in surrounds:
            current = typed[:i] + surround + typed[i+1:]
            if suggested['word']==current:
                return True
    return False


def check_sound_similarity(word1, word2):
    if not word1 or not word2:
        return False

    word1, word2 = re.sub(r'(\w)(?=\1)', '', word1), re.sub(r'(\w)(?=\1)', '', word2)

    if (word1.replace('y', 'i') == word2.replace('y', 'i')) and (word1[0]!='y' and word2[0]!='y'):
        word1 = word1.replace('y','i')
        word2 = word2.replace('y','i')

    if word1 == word2:
        return True
    if word1.replace('th', 't') == word2.replace('th', 't') and word1[0]!='t' and word2[0]!='t':
        return True
    if word1.replace('ashi', 'ati') == word2.replace('ashi', 'ati') and word1[0:3]!='ashi' and word2[0:3]!='ashi':
        return True
    if word1.replace('asha', 'ati') == word2.replace('asha', 'ati') and word1[0:3]!='asha' and word2[0:3]!='asha':
        return True
    if word1.replace('ph', 'f') == word2.replace('ph', 'f'):
        return True
    if word1.replace('hr', 'r') == word2.replace('hr', 'r'):
        return True
    if word1.replace('oo', 'u') == word2.replace('oo', 'u'):
        return True
    if word1.replace('sh', 's') == word2.replace('sh', 's'):
        return True
    if word1.replace('ck', 'c') == word2.replace('ck', 'c'):
        return True
    if word1.replace('k', 'c') == word2.replace('k', 'c'):
        return True
    if word1.replace('w', 'v') == word2.replace('w', 'v'):
        return True
    if word1.replace('o', 'u') == word2.replace('o', 'u'):
        return True
    if word1.replace('e', 'i') == word2.replace('e', 'i'):
        return True
    if word1.replace('a', 'e') == word2.replace('a', 'e'):
        return True
    if word1.replace('z', 's') == word2.replace('z', 's') and (word1[0]!='z' and word2[0]!='z'):
        return True
    if word1.replace('z', 'j') == word2.replace('z', 'j'):
        return True
    if word1.replace('ch', 'c') == word2.replace('ch', 'c') and (word1[0:2]!='ch' and word2[0:2]!='ch'):
        return True
    if word1.replace('ch', 'k') == word2.replace('ch', 'k'):
        return True
    if word1.replace('cq', 'q') == word2.replace('cq', 'q'):
        return True
    return False


def get_soundex(word):
    word = word.lower()
    word_startswith = {'aa':'a', "oo":'u', 'q':'k', 'e':'i', 'b':'v', 'ph':'f','j':'z', 'hr':'r', 'ks':'s', 'dny':'jn', 'gny':'jn'} # k:->c??
    for key in word_startswith.keys():
        if word.startswith(key):
            word = word.replace(key, word_startswith[key],1)
            break
    word = word.upper()
    soundex = ""
    soundex += word[0]
    dictionary = {"BFPWV": "1", "CGJKQSXZ":"2", "DT":"3", "L":"4", "MN":"5", "R":"6", "AEIOUH":"","Y":"7"}
    for char in word[1:]:
        for key in dictionary.keys():
            if char in key:
                code = dictionary[key]
                if code != soundex[-1]:
                    soundex += code
    soundex = soundex.replace(".", "")
    soundex = soundex[:8].ljust(8, "0");
    return soundex


def generate_all_possible_regex(word):
    regex_comb = []
    for i in range(1,len(word)-2):
        for j in range(i+1,len(word)-1):
            for k in range(j+1,len(word)):
                current = word[:i] + '[a-z]{0,2}' + word[i+1:j] + '[a-z]{0,2}' + word[j+1:k] + '[a-z]{0,2}' + word[k+1:]
                regex_comb.append(current)
    for i in range(1,len(word)-1):
        for j in range(i+1,len(word)):
            current = word[:i] + '[a-z]{0,2}' + word[i+1:j] + '[a-z]{0,2}' + word[j+1:]
            regex_comb.append(current)

    for i in range(1,len(word)):
        current = word[:i] + '[a-z]{0,2}' + word[i+1:]
        regex_comb.append(current)

    return regex_comb


def search_possiblities(word):
    possibilities = []
    # current_word = 'futboll'
    n = len(word)
    all_regex = generate_all_possible_regex(word)
    for curr in all_regex:
        value = '^' + curr + '$'
        search = {'word' : {'$regex':value}}
        results = collection.find(search).limit(10)
        for i in results:
            # print(value)
            possibilities.append({'word' : i['word'], 'frequency' : i['frequency']})

    possibilities = list({v['word']:v for v in possibilities}.values())
    return possibilities


def get_topk(scores):
    new_scores = sorted(scores,key = lambda k:k['score'],reverse=True)
    # print(new_scores)
    # If scores are comparable in the range of 0-5%, we will use frequency as final deciding parameter
    scores_percentage = [float(f['score']/new_scores[0]['score']) for f in new_scores[1:3]]
    base_frequency = new_scores[0]['frequency']
    for i in range(len(scores_percentage)):
        if scores_percentage[i] > 0.95:
            if base_frequency < new_scores[i+1]['frequency']:
                frequency_ratio = float(float(new_scores[i+1]['frequency'])/float(base_frequency))
                current_score = new_scores[i+1]['score']
                current_score += (1-current_score)*(frequency_wt)*min(frequency_ratio,1)
                new_scores[i+1]['score'] = current_score
    new_scores = sorted(scores,key = lambda k:k['score'],reverse=True)
    return new_scores


# TODO: Replace ph with f also
def lambda_handler(typed):
    #Generate All Combinations
    #Check All Regex Combinations to find Possible Words
    #Check soundex and check_sound_similarity

    possibilities = search_possiblities(typed)
    # print(possibilities)
    current_time = round(time.time()*1000)
    current_soundex = get_soundex(typed)
    phonetic_shortlisted = []
    nearby_shortlisted = []
    bagging_shortlisted = []
    rest = []
    scores = []
    for possiblity in possibilities:
        # print(possiblity)
        current_score = possiblity
        possible_soundex = get_soundex(possiblity['word'])
        phonetic_flag = False
        soundex_flag = False
        bagging_flag = False
        surrounding_key_flag = False
        if possible_soundex==current_soundex:
            phonetic_shortlisted.append(possiblity)
            soundex_flag = True
        if check_sound_similarity(typed,possiblity['word']):
            phonetic_shortlisted.append(possiblity)
            phonetic_flag = True
        # Jaro Winkler Keeps Misplace Elements into Account like ('Gourav' and 'Goruav')
        if bagging_method(typed,possiblity['word']):
            bagging_shortlisted.append(possiblity)
            bagging_flag = True
        if check_surrounding(typed,possiblity):
            nearby_shortlisted.append(possiblity)
            surrounding_key_flag = True

        if not soundex_flag and not phonetic_flag and not bagging_flag and not surrounding_key_flag:
            rest.append(possiblity)
            current_score['score'] = get_score(typed,possiblity['word'])
            scores.append(current_score)
        else:
            current_score['score'] = get_score(typed,possiblity['word'],soundex_flag,phonetic_flag,bagging_flag,surrounding_key_flag)
            scores.append(current_score)
        # print(check_surrounding(typed,possiblity))

    scores = list({v['word']:v for v in scores}.values())
    scores = get_topk(scores)
    output = {'typed':typed}
    for i in range(len(scores)):
        if i==3:
            break
        else:
            current_word = 'word' + str(i+1)
            current_score = 'score' + str(i+1)
            output[current_word] = scores[i]['word']
            output[current_score] = scores[i]['score']

    return output


if __name__ == '__main__':
    words = ['futboll','notebuk','mishun','moshun','ganaral','knolege','greej','beautiul','chagnes','compeoter','curant','nashanal',
             'funcshen','chemikal','chemistri','phisiks','culcher','secshion','elefant','hosre','littke','wrking','imsyde','partukular',
             'inhreent','keybord','relace','protien','juce','tee','lite','wach','cuntain','hier','tolk','ultima','lojikali','lust',
             'monga','mashine','mekanikal','artritis','crome','brij','backup','alfa','crist','dolfin','feture','pither','tere', 'fuly' ,
             'automatik','wamyed','avveptamce','assption','appolo','bouket','cheke','fum','forat','deat','faceletate','fadar','furrry',
             'fashhhion','galakc','zoofeelia','jamaka','jkrta','jejus','jest','jerelleri','iyentical','idnore','luv','willimg','croud',
             'delli','ishtanbool','luk','hewet','skool','refrigreator','electricty','vegetrerian','tropicial','evergren','ridiclos',
             'agregate','registred','industy','spectaklar','amzon','pilow','stationery','colection','stres','straen','powerfgl',
             'opinipn','dokument']

    # words = ['mikesoft']
    # more = ['this','very','important','let','me','know','what','can','doable','about','particular','words','increase']
    print(len(words))
    data = []
    now = round(time.time()*1000)
    for word in words:
        print(word)
        output = lambda_handler(word.lower())
        current_time = round(time.time()*1000)
        output['time'] = current_time-now
        now = current_time
        data.append(output)
    df = pd.DataFrame(data)
    path = os.getcwd() + 'result.xlsx'
    print(path)
    df.to_excel(path)
    print(data)
    # print(dict(psutil.virtual_memory()._asdict()))