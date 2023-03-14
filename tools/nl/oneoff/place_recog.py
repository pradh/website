

# dict structure:
# word --> [[remaining words], dcid, [containing places dcid]] ...]

#geoId/0668000,City,San Jose,"Earth,country/USA,geoId/06,geoId/06085,northamerica,usc/PacificDivision,usc/WestRegion,wikidataId/Q213205,wikidataId/Q3271856",983489

places = {}

def okLine(line):
    lx = line.split('\"')
    if (len(lx) != 3):
        return False
    ln = lx[0].split(',')
    if (len(ln) != 4):
        return False
    return True

def loadPlaces (places_csv):
    f = open(places_csv)
    ln = 0
    for line in f:
        if (ln < 2):
            ln = ln + 1
        elif (okLine(line)):
            line = line.strip()
            (pre, containingStr, population) = line.split('\"')
            (dcid, placeType, name, ignore) = pre.split(',')
            containing = containingStr.split(',')
            nameParts = name.split(' ')
            if (nameParts[0] not in places) :
                places[nameParts[0]] = []
            places[nameParts[0]].append([nameParts, dcid, containing])

def findPlaceCand (tokens):
    if (len(tokens) == 0):
        return None
    next = tokens[0]
    if (next not in places):
        return [0, None]
    suffixes = places[next]
    numTokens = 1
    candidates = []
    for cand in suffixes:
        n = 0
        notFound = False
        for w in cand[0]:            
            if ((len(tokens) < n) or (w != tokens[n])):
                notFound = True
                break
            n = n + 1
        if (numTokens < n):
            numTokens = n
        if (not notFound):
            candidates.append(cand)
    return [numTokens, candidates]


def replaceTokensWithCandidates (tokens):
    ans = []
    while (len(tokens) > 0):
        next = findPlaceCand(tokens)
        if (next[0] > 0):
            ans.append(next[1])
            tokens = tokens[next[0]:]
        else:
            ans.append(tokens[0])
            tokens = tokens[1:]
    return ans

def tokenize (str):
    ans = []
    n = 0
    inSpace = False
    nextStr = []
    while (n < len(str)):
        nc = str[n]
        if (nc == ' '):
            inSpace = True
            if (len(nextStr) > 0):
                ans.append("".join(nextStr))
                nextStr = []
        elif (nc == ','):
            inSpace == True
            if (len(nextStr) > 0):
                ans.append("".join(nextStr))
                ans.append(',')
                nextStr = []
        else:
            nextStr.append(nc)
        n = n + 1
    if (len(nextStr) > 0):
        ans.append("".join(nextStr))
    return ans

def getNextTokForContainedIn(seq, n):
    if (len(seq) > n+2 and seq[n+1] == ',' and not isinstance(seq[n+2], str)):
        return 3, seq[n+2];
    elif (len(seq) > n+1 and not isinstance(seq[n+1], str)):
        return 2, seq[n+1];
    else:
        return 0, None

def combineContainedIn (seq):
    n = 0
    ans = []
    while (n < len(seq)):        
        tok = seq[n]
        if (isinstance(tok, str)):
            n = n + 1
            ans.append(tok)
            continue
        numTok, nextTok = getNextTokForContainedIn(seq, n)
        if (numTok == 0):
            n = n + 1
            ans.append(tok)
            continue
        collapsed = combineContainedInInt(tok, nextTok)
        if (not collapsed):
            n = n + 1
            ans.append(tok)
        else :
            n = n + numTok
            ans.append(collapsed)
    return ans

def combineContainedInInt (tok, nextTok):
    for it1 in tok:
        for containingDcid in it1[2]:
            for it2 in nextTok:
                if (containingDcid == it2[1]):
                    return it1
    return None

loadPlaces("USGeos.csv")

str1 = "the birds in San Jose are chirpy"
str2 = "the birds in San Jose, California are chirpy"
str3 = "the birds in San Jose California are chirpy"
str4 = "the birds in San Jose, Mountain View and Sunnyvale are chirpy"


for strx in [str1, str2, str3, str4]:
    toks =  replaceTokensWithCandidates(tokenize(strx))
    print("\n\n" + strx)
    print(combineContainedIn(toks))

            
                
        
