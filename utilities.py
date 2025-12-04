import os;
os.system("");
from crewai import Agent, Task, Crew;
import signal;
import sys;

def getApiKey():
    apiKey = open(".env", "r", encoding="utf-8").read();
    return apiKey;

def fileExists(filePath):
    return os.path.exists(filePath);

def deleteFile(filePath):
    os.remove(filePath);

def readFile(filePath):
    if(os.path.exists(filePath) == False):
        return "";
    return open(filePath, "r", encoding="utf-8").read();

def writeFile(filePath, contents):
    open(filePath, "w", encoding="utf-8").write(contents);

def readBinaryFile(filePath):
    return bytearray(open(filePath, "rb").read());

def writeBinaryFile(filePath, blob):
    open(filePath, "wb").write(blob);

def staticLink(filePath):
    exec(readFile(filePath), globals());

def stringToList(s):
    i = 0;
    list = [];
    while i < len(s)-1:
        if(s[i] == '\n' and s[i+1] == '\n'):
            list.append(cleanLeadingTrailingSpace(s[0:i:]));
            s = s[i+2::];
            i = 0;
        else:
            i += 1;
    if(cleanLeadingTrailingSpace(s) != ""):
        list.append(cleanLeadingTrailingSpace(s));
    return list;

def listToString(list):
    s = "";
    for i in range(len(list)):
        s += (list[i] + "\n\n");
    return s;

apiKeyActivated = False;
def runAgent(role, goal, backstory, task, expectedOutput, inputMap, debugMode):
    global apiKeyActivated;
    if(apiKeyActivated == False):
        apiKeyActivated = True;
        os.environ["OPENAI_MODEL_NAME"] = "gpt-5";
        os.environ["OPENAI_API_KEY"] = getApiKey();
    agent = Agent(role = role, goal = goal, backstory = backstory, verbose = debugMode);
    task = Task(description = task, expected_output = expectedOutput, agent = agent);
    crew = Crew(agents = [agent], tasks = [task], verbose = debugMode);
    output = str(crew.kickoff(inputs = inputMap));
    return output;
