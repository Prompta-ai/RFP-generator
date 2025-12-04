import struct;
import webbrowser;
import threading;
import os;
import logging;
import warnings;
import random;
from dataclasses import dataclass;
import types;
import django;
from django.core.management import execute_from_command_line;
from django.http import HttpResponse, FileResponse;
from django.core.wsgi import get_wsgi_application;
from wsgiref.simple_server import make_server, WSGIServer;
from socketserver import ThreadingMixIn;
from threading import Event;

def readInt(blob, offset):
    return struct.unpack_from("<i", blob, offset)[0];

def readFloat(blob, offset):
    return struct.unpack_from("<f", blob, offset)[0];

def readString(blob, offset, bytesCount):
    return blob[offset:offset + bytesCount:].decode("utf-8");

def readBlob(blob, offset, bytesCount):
    return blob[offset:offset + bytesCount:];

def allocateBlob(bytesCount):
    return bytearray(bytesCount);

def getStringBytesCount(s):
    return len(s.encode("utf-8"));

def writeInt(blob, offset, n):
    struct.pack_into("<i", blob, offset, n);
    
def writeFloat(blob, offset, f):
    struct.pack_into("<f", blob, offset, f);

def writeString(blob, offset, s):
    stringBlob = s.encode("utf-8");
    blob[offset:offset+len(stringBlob):] = stringBlob;
    
def writeBlob(blob, offset, s):
    blob[offset:offset+len(s):] = s;

def getListOfProjects():
    filesAndFolders = os.listdir(".");
    output = [];
    for i in filesAndFolders:
        if(len(i) > 5 and i[len(i)-5::] == ".proj"):
            output.append(int(i[0:len(i)-5:]));
    return output;

def getJSMainFunction(request):
    return FileResponse(readFile("index.html"), content_type="text/html");

def sendBlob(blob):
    return HttpResponse(bytes(blob), content_type= "application/octet-stream");

def DLL_EXPORT_API_readProjectList(request):
    projectHashes = getListOfProjects();
    projectNames = [];
    projectNameLengths = [];
    for i in range(len(projectHashes)):
        projectBlob = readBinaryFile(str(projectHashes[i]) + ".proj");
        nameOffset = readInt(projectBlob, 0);
        nameLength = readInt(projectBlob, nameOffset);
        projectNames.append(readString(projectBlob, nameOffset + 4, nameLength));
        projectNameLengths.append(nameLength);
    projectOffsets = [];
    currentOffset = 4 + 4 * len(projectHashes);
    for i in range(len(projectHashes)):
        projectOffsets.append(currentOffset);
        currentOffset += (4 + 4 + projectNameLengths[i]);
    blob = allocateBlob(currentOffset);
    currentOffset = 0;
    writeInt(blob, currentOffset, len(projectHashes));
    currentOffset += 4;
    for i in range(len(projectHashes)):
        writeInt(blob, currentOffset, projectOffsets[i]);
        currentOffset += 4;
    for i in range(len(projectHashes)):
        writeInt(blob, currentOffset, projectHashes[i]);
        currentOffset += 4;
        writeInt(blob, currentOffset, projectNameLengths[i]);
        currentOffset += 4;
        writeString(blob, currentOffset, projectNames[i]);
        currentOffset += projectNameLengths[i];
    return sendBlob(blob);

def DLL_EXPORT_API_uploadResponse(request):
    fileType = readInt(request.body, 0);
    fileSize = readInt(request.body, 4);
    file = readBlob(request.body, 8, fileSize);
    isPDF = (fileType == 1);
    DLL_EXPORT_addPreviousResponseToDataBase(file, isPDF);
    return sendBlob(allocateBlob(0));

@dataclass
class Question:
    canAutomate: int;
    deleteLastResponse: int;
    summary: str;
    question: str;
    responses: list;

@dataclass
class Project:
    name: str;
    generalInfo: str;
    questions: list;

def getQuestionByteLength(question):
    length = 28;
    length += 8 * len(question.responses);
    length += getStringBytesCount(question.question);
    length += getStringBytesCount(question.summary);
    for i in question.responses:
        length += getStringBytesCount(i);
    return length;

def encodeQuestionToBlob(question):
    blob = allocateBlob(getQuestionByteLength(question));
    currentOffset = 0;
    writeInt(blob, currentOffset, question.canAutomate);
    currentOffset += 4;
    writeInt(blob, currentOffset, question.deleteLastResponse);
    currentOffset += 4;
    writeInt(blob, currentOffset, 28 + 4 * len(question.responses));
    currentOffset += 4;
    questionLength = getStringBytesCount(question.question);
    writeInt(blob, currentOffset, questionLength);
    currentOffset += 4;
    writeInt(blob, currentOffset, 28 + 4 * len(question.responses) + questionLength);
    currentOffset += 4;
    summaryLength = getStringBytesCount(question.summary);
    writeInt(blob, currentOffset, summaryLength);
    currentOffset += 4;
    writeInt(blob, currentOffset, len(question.responses));
    currentOffset += 4;
    responseLengths = [];
    responseLengthBlobRegionStart = currentOffset;
    for i in question.responses:
        thisReponseLength = getStringBytesCount(i);
        responseLengths.append(thisReponseLength);
        currentOffset += 4;
    writeString(blob, currentOffset, question.question);
    currentOffset += questionLength;
    writeString(blob, currentOffset, question.summary);
    currentOffset += summaryLength;
    for i in range(len(question.responses)):
        writeInt(blob, currentOffset, responseLengths[i]);
        currentOffset += 4;
        writeString(blob, currentOffset, question.responses[i]);
        currentOffset += responseLengths[i];
        writeInt(blob, responseLengthBlobRegionStart, currentOffset - 4 - responseLengths[i]);
        responseLengthBlobRegionStart += 4;
    return blob;

def saveProject(projectHash, project):
    blobLength = 12;
    offsetToName = 12;
    nameLength = getStringBytesCount(project.name);
    blobLength += 4 + nameLength;
    offsetToGeneralInfo = blobLength;
    generalInfoLength = getStringBytesCount(project.generalInfo);
    blobLength += 4 + generalInfoLength;
    offsetToQuestions = blobLength;
    questionLengths = [];
    questionOffsets = [];
    blobLength += 4 + 8 * len(project.questions);
    for i in project.questions:
        thisQuestionLength = getQuestionByteLength(i);
        questionOffsets.append(blobLength);
        questionLengths.append(thisQuestionLength);
        blobLength += thisQuestionLength;
    blob = allocateBlob(blobLength);
    currentOffset = 0;
    writeInt(blob, currentOffset, offsetToName);
    currentOffset += 4;
    writeInt(blob, currentOffset, offsetToGeneralInfo);
    currentOffset += 4;
    writeInt(blob, currentOffset, offsetToQuestions);
    currentOffset += 4;
    writeInt(blob, currentOffset, nameLength);
    currentOffset += 4;
    writeString(blob, currentOffset, project.name);
    currentOffset += nameLength;
    writeInt(blob, currentOffset, generalInfoLength);
    currentOffset += 4;
    writeString(blob, currentOffset, project.generalInfo);
    currentOffset += generalInfoLength;
    writeInt(blob, currentOffset, len(project.questions));
    currentOffset += 4;
    for i in questionOffsets:
        writeInt(blob, currentOffset, i);
        currentOffset += 4;
    for i in questionLengths:
        writeInt(blob, currentOffset, i);
        currentOffset += 4;
    for i in range(len(project.questions)):
        writeBlob(blob, currentOffset, encodeQuestionToBlob(project.questions[i]));
        currentOffset += questionLengths[i];
    
    writeBinaryFile(str(projectHash) + ".proj", blob);

    """
    struct Question {
        layout(location = 0) int canAutomate;
        layout(location = 4) int deleteLastResponse;
        layout(location = 8) int offsetToQuestion;
        layout(location = 12) int questionLength;
        layout(location = 16) int summaryOffset;
        layout(location = 20) int summaryLength;
        layout(location = 24) int responseCount;
        layout(location = 28) int responseOffsets[responseCount];
        layout(location = offsetToQuestion) char question[questionLength];
        layout(location = summaryOffset) char summary[summaryLength];
        layout(location = responseOffsets[index]) int responseLengths[responseCount];
        layout(location = responseOffsets[index] + 4) char responses[responseCount];
    };
    layout(location = 0) int offsetToName;
    layout(location = 4) int offsetToGeneralInfo;
    layout(location = 8) int offsetToQuestions;
    layout(location = offsetToName) int nameLength;
    layout(location = offsetToName + 4) char name[nameLength];
    layout(location = offsetToGeneralInfo) int generalInfoLength;
    layout(location = offsetToGeneralInfo + 4) char generalInfo[generalInfoLength];
    layout(location = offsetToQuestions) int numberOfQuestions;
    layout(location = offsetToQuestions + 4) int questionOffset[numberOfQuestions];
    layout(location = offsetToQuestions + 4 + 4 * numberOfQuestions) int questionLengths[numberOfQuestions];
    layout(location = questionOffset[index]) Question questions[numberOfQuestions];
    """

lockAutoGenerateAnswer = threading.Lock();
totalLengthAutoGenerateAnswer = 0;
processedLengthAutoGenerateAnswer = 0;
def processAutoGenerateAnswer(question, generalInfo, databaseInfo):
    if(question.automatable == True):
        output = Question(canAutomate=True, deleteLastResponse=False, summary="", question=question.question, responses=[DLL_EXPORT_writeResponse(question.question, generalInfo, databaseInfo)]);
    else:
        output = Question(canAutomate=False, deleteLastResponse=False, summary="", question=question.question, responses=[]);
    global lockAutoGenerateAnswer;
    global totalLengthAutoGenerateAnswer;
    global processedLengthAutoGenerateAnswer;
    lockAutoGenerateAnswer.acquire();
    processedLengthAutoGenerateAnswer += 1;
    global API_MSG_projectCreationMessage;
    API_MSG_projectCreationMessage = "generating responses for applicable questions... " + str(int(100.0 * float(processedLengthAutoGenerateAnswer) / float(totalLengthAutoGenerateAnswer))) + "%";
    lockAutoGenerateAnswer.release();
    return output;

ignoreRFPInterruptHandler = Event();
ignoreRFPUserInput = 0;
def DLL_EXPORT_API_receiveIgnoreRFPInterruptResponse(request):
    response = readInt(request.body, 0);
    global ignoreRFPInterruptHandler;
    global ignoreRFPUserInput;
    ignoreRFPUserInput = response;
    ignoreRFPInterruptHandler.set();
    return sendBlob(allocateBlob(0));

def DLL_EXPORT_API_createNewProject(request):
    global API_MSG_projectCreationMessage;
    global ignoreRFPInterruptHandler;
    global ignoreRFPUserInput;
    fileType = readInt(request.body, 0);
    projectNameBytesLength = readInt(request.body, 4);
    projectName = readString(request.body, 8, projectNameBytesLength);
    fileSize = readInt(request.body, 8 + projectNameBytesLength);
    file = readBlob(request.body, 12 + projectNameBytesLength, fileSize);
    ignoreRFP = DLL_EXPORT_checkIfIgnore(file, fileType);
    for i in ignoreRFP:
        API_MSG_projectCreationMessage = "IGNORE_RFP_INTERRUPT " + i;
        ignoreRFPInterruptHandler.clear();
        ignoreRFPUserInput = 0;
        ignoreRFPInterruptHandler.wait();
        if(ignoreRFPUserInput == 1):
            API_MSG_projectCreationMessage = "DONE";
            return sendBlob(allocateBlob(0));
    rawQuestionsList = [];
    generalInfo = DLL_EXPORT_parseIncomingRFP(rawQuestionsList);
    projectHash = 0;
    while(True):
        projectHash = int(1000000.0 * random.random());
        if(fileExists(str(projectHash) + ".proj") == False):
            break;
    
    project = Project(name=projectName, generalInfo=generalInfo, questions=[]);
    databaseInfo = readFile("database.txt");
    API_MSG_projectCreationMessage = "generating responses for applicable questions...";

    global totalLengthAutoGenerateAnswer;
    global processedLengthAutoGenerateAnswer;
    totalLengthAutoGenerateAnswer = len(rawQuestionsList);
    processedLengthAutoGenerateAnswer = 0;
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = [];
        for i in rawQuestionsList:
            futures.append(executor.submit(processAutoGenerateAnswer, i, generalInfo, databaseInfo));
        for f in futures:
            result = f.result();
            project.questions.append(result);

    questionsList = [];
    for i in project.questions:
        questionsList.append(i.question);
    questionsList = DLL_EXPORT_summariseQuestions(questionsList);
    for i in range(len(project.questions)):
        project.questions[i].summary = questionsList[i];
    saveProject(projectHash, project);
    API_MSG_projectCreationMessage = "DONE";
    return sendBlob(allocateBlob(0));

API_MSG_projectCreationMessage = "";
def DLL_EXPORT_API_respondProjectCreationSample(request):
    global API_MSG_projectCreationMessage;
    messageLength = getStringBytesCount(API_MSG_projectCreationMessage);
    blob = allocateBlob(4 + 4 + messageLength);
    writeInt(blob, 0, 0);
    if(API_MSG_projectCreationMessage == "DONE"):
        writeInt(blob, 0, 1);
    elif(len(API_MSG_projectCreationMessage) > 21 and API_MSG_projectCreationMessage[0:21:] == "IGNORE_RFP_INTERRUPT "):
        message = API_MSG_projectCreationMessage[21::];
        API_MSG_projectCreationMessage = "confirming if to ignore RFP...";
        messageLength = getStringBytesCount(message);
        blob = allocateBlob(4 + 4 + messageLength);
        writeInt(blob, 0, 2);
        writeInt(blob, 4, messageLength);
        writeString(blob, 8, message);
        return sendBlob(blob);
    writeInt(blob, 4, messageLength);
    writeString(blob, 8, API_MSG_projectCreationMessage);
    return sendBlob(blob);

API_MSG_uploadResponseMessage = "";
def DLL_EXPORT_API_uploadResponseSample(request):
    global API_MSG_uploadResponseMessage;
    messageLength = getStringBytesCount(API_MSG_uploadResponseMessage);
    blob = allocateBlob(4 + 4 + messageLength);
    writeInt(blob, 0, 0);
    if(API_MSG_uploadResponseMessage == "DONE"):
        writeInt(blob, 0, 1);
    writeInt(blob, 4, messageLength);
    writeString(blob, 8, API_MSG_uploadResponseMessage);
    return sendBlob(blob);

def decodeQuestion(blob):
    canAutomate = readInt(blob, 0);
    deleteLastResponse = readInt(blob, 4);
    questionOffset = readInt(blob, 8);
    questionLength = readInt(blob, 12);
    summaryOffset = readInt(blob, 16);
    summaryLength = readInt(blob, 20);
    responseCount = readInt(blob, 24);
    responseOffsets = [];
    for i in range(responseCount):
        responseOffsets.append(readInt(blob, 28 + 4 * i));
    question = readString(blob, questionOffset, questionLength);
    summary = readString(blob, summaryOffset, summaryLength);
    responses = [];
    for i in range(responseCount):
        length = readInt(blob, responseOffsets[i]);
        response = readString(blob, responseOffsets[i] + 4, length);
        responses.append(response);
    return Question(canAutomate=canAutomate, deleteLastResponse=deleteLastResponse, summary=summary, question=question, responses=responses);

currentOpenProject = None;
currentOpenProjectHash = -1;
def DLL_EXPORT_API_openProject(request):
    projectHash = readInt(request.body, 0);
    fileBlob = readBinaryFile(str(projectHash) + ".proj");
    nameOffset = readInt(fileBlob, 0);
    generalInfoOffset = readInt(fileBlob, 4);
    questionsOffset = readInt(fileBlob, 8);
    nameLength = readInt(fileBlob, nameOffset);
    projectName = readString(fileBlob, nameOffset + 4, nameLength);
    generalInfoLength = readInt(fileBlob, generalInfoOffset);
    generalInfo = readString(fileBlob, generalInfoOffset + 4, generalInfoLength);
    questionCount = readInt(fileBlob, questionsOffset);
    questionLengths = [];
    questionOffsets = [];
    for i in range(questionCount):
        questionOffsets.append(readInt(fileBlob, questionsOffset + 4 + 4 * i));
        questionLengths.append(readInt(fileBlob, questionsOffset + 4 + 4 * questionCount + 4 * i));
    questions = [];
    for i in range(questionCount):
        questions.append(decodeQuestion(readBlob(fileBlob, questionOffsets[i], questionLengths[i])));
    global currentOpenProject;
    currentOpenProject = Project(name=projectName, generalInfo=generalInfo, questions=questions);
    global currentOpenProjectHash;
    currentOpenProjectHash = projectHash;
    """
    layout(location = 0) int questionCount;
    layout(location = 4) int questionOffsets[questionCount];
    layout(location = 4 + 4 * questionCount) int questionLengths[questionCount];
    layout(location = questionOffsets[index]) char question[questionLengths[index]];
    """
    questionsCount = len(currentOpenProject.questions);
    blobLength = 4 + 8 * questionsCount;
    questionOffsets = [];
    questionLengths = [];
    for i in currentOpenProject.questions:
        length = getStringBytesCount(i.summary);
        questionLengths.append(length);
        questionOffsets.append(blobLength);
        blobLength += length;
    blob = allocateBlob(blobLength);
    writeInt(blob, 0, questionsCount);
    for i in range(questionsCount):
        writeInt(blob, 4 + 4 * i, questionOffsets[i]);
        writeInt(blob, 4 + 4 * questionsCount + 4 * i, questionLengths[i]);
        writeString(blob, questionOffsets[i], currentOpenProject.questions[i].summary);
    return sendBlob(blob);

def DLL_EXPORT_API_getQuestion(request):
    questionNumber = readInt(request.body, 0);
    global currentOpenProject;
    blobLength = 16;
    questionOffset = 16;
    question = "(choose a question to open from the left)";
    if(questionNumber != -1):
        question = currentOpenProject.questions[questionNumber].question;
    questionLength = getStringBytesCount(question);
    blobLength += questionLength;
    response = "";
    if(questionNumber != -1 and len(currentOpenProject.questions[questionNumber].responses) > 0):
        response = currentOpenProject.questions[questionNumber].responses[len(currentOpenProject.questions[questionNumber].responses) - 1];
    responseOffset = blobLength;
    responseLength = getStringBytesCount(response);
    blobLength += responseLength;
    """
    layout(location = 0) int questionOffset;
    layout(location = 4) int questionLength;
    layout(location = 8) int responseOffset;
    layout(location = 12) int responseLength;
    layout(location = questionOffset) char question[questionLength];
    layout(location = responseOffset) char response[responseLength];
    """
    blob = allocateBlob(blobLength);
    writeInt(blob, 0, questionOffset);
    writeInt(blob, 4, questionLength);
    writeInt(blob, 8, responseOffset);
    writeInt(blob, 12, responseLength);
    writeString(blob, questionOffset, question);
    writeString(blob, responseOffset, response);
    return sendBlob(blob);

def saveResponseCustomBlob(blob):
    global currentOpenProject;
    global currentOpenProjectHash;
    questionNumber = readInt(blob, 0);
    implicit = readInt(blob, 4);
    latestResponse = "";
    if(len(currentOpenProject.questions[questionNumber].responses) > 0):
        latestResponse = currentOpenProject.questions[questionNumber].responses[len(currentOpenProject.questions[questionNumber].responses) - 1];
    responseLength = readInt(blob, 8);
    response = readString(blob, 12, responseLength);
    if(latestResponse == response):
        return sendBlob(allocateBlob(0));
    if(currentOpenProject.questions[questionNumber].deleteLastResponse == 1):
        currentOpenProject.questions[questionNumber].responses.pop();
    currentOpenProject.questions[questionNumber].responses.append(response);
    currentOpenProject.questions[questionNumber].deleteLastResponse = implicit;
    saveProject(currentOpenProjectHash, currentOpenProject);
    return sendBlob(allocateBlob(0));

def DLL_EXPORT_API_saveResponse(request):
    return saveResponseCustomBlob(request.body);

def DLL_EXPORT_API_terminateServer(request):
    syscall9();

def DLL_EXPORT_API_terminateWithSave(request):
    saveResponseCustomBlob(request.body);
    DLL_EXPORT_API_terminateServer(request);

def DLL_EXPORT_API_revertResponse(request):
    global currentOpenProject;
    global currentOpenProjectHash;
    questionNumber = readInt(request.body, 0);
    currentOpenProject.questions[questionNumber].deleteLastResponse = 0;
    if(len(currentOpenProject.questions[questionNumber].responses) > 0):
        currentOpenProject.questions[questionNumber].responses.pop();
    saveProject(currentOpenProjectHash, currentOpenProject);
    return sendBlob(allocateBlob(0));

def DLL_EXPORT_API_generateResponse(request):
    global currentOpenProjectHash;
    global currentOpenProject;
    questionNumber = readInt(request.body, 0);
    response = DLL_EXPORT_writeResponse(currentOpenProject.questions[questionNumber].question, currentOpenProject.generalInfo, readFile("database.txt"));
    currentOpenProject.questions[questionNumber].responses.append(response);
    currentOpenProject.questions[questionNumber].deleteLastResponse = 0;
    saveProject(currentOpenProjectHash, currentOpenProject);
    return sendBlob(allocateBlob(0));

def DLL_EXPORT_API_enhanceResponse(request):
    global currentOpenProjectHash;
    global currentOpenProject;
    questionNumber = readInt(request.body, 0);
    questionNumberToSend = readInt(request.body, 4);
    instructionsLength = readInt(request.body, 8);
    instructions = readString(request.body, 12, instructionsLength);
    previousResponse = "";
    if(len(currentOpenProject.questions[questionNumber].responses) > 0):
        previousResponse = currentOpenProject.questions[questionNumber].responses[len(currentOpenProject.questions[questionNumber].responses) - 1];
    question = "";
    infoDatabase = "";
    if(questionNumberToSend != -1):
        question = currentOpenProject.questions[questionNumberToSend].question;
        infoDatabase = readFile("database.txt");
    response = DLL_EXPORT_enhanceResponse(previousResponse, instructions, questionNumberToSend, question, infoDatabase);
    currentOpenProject.questions[questionNumber].responses.append(response);
    currentOpenProject.questions[questionNumber].deleteLastResponse = 0;
    saveProject(currentOpenProjectHash, currentOpenProject);
    return sendBlob(allocateBlob(0));

def DLL_EXPORT_API_getDatabase(request):
    contents = readFile("database.txt");
    length = getStringBytesCount(contents);
    blob = allocateBlob(4 + length);
    writeInt(blob, 0, length);
    writeString(blob, 4, contents);
    return sendBlob(blob);

def DLL_EXPORT_API_setDatabase(request):
    length = readInt(request.body, 0);
    contents = readString(request.body, 4, length);
    writeFile("database.txt", contents);
    return sendBlob(allocateBlob(0));

def DLL_EXPORT_API_getRequirements(request):
    contents = readFile("requirements.txt");
    length = getStringBytesCount(contents);
    blob = allocateBlob(4 + length);
    writeInt(blob, 0, length);
    writeString(blob, 4, contents);
    return sendBlob(blob);

def DLL_EXPORT_API_setRequirements(request):
    length = readInt(request.body, 0);
    contents = readString(request.body, 4, length);
    writeFile("requirements.txt", contents);
    return sendBlob(allocateBlob(0));

def DLL_EXPORT_API_getGeneralInfo(request):
    global currentOpenProject;
    contents = currentOpenProject.generalInfo;
    length = getStringBytesCount(contents);
    blob = allocateBlob(4 + length);
    writeInt(blob, 0, length);
    writeString(blob, 4, contents);
    return sendBlob(blob);

def DLL_EXPORT_API_setGeneralInfo(request):
    global currentOpenProject;
    global currentOpenProjectHash;
    length = readInt(request.body, 0);
    contents = readString(request.body, 4, length);
    currentOpenProject.generalInfo = contents;
    saveProject(currentOpenProjectHash, currentOpenProject);
    return sendBlob(allocateBlob(0));

def DLL_EXPORT_API_deleteProject(request):
    projectHash = readInt(request.body, 0);
    deleteFile(str(projectHash) + ".proj");
    return sendBlob(allocateBlob(0));

def DLL_EXPORT_API_editDatabaseContents(request):
    instructionsLength = readInt(request.body, 0);
    instructions = readString(request.body, 4, instructionsLength);
    DLL_EXPORT_editDatabaseContents(instructions);
    return sendBlob(allocateBlob(0));

API_MSG_generateDocxMessage = "";
def DLL_EXPORT_API_generateDocxSample(request):
    global API_MSG_generateDocxMessage;
    messageLength = getStringBytesCount(API_MSG_generateDocxMessage);
    blob = allocateBlob(4 + 4 + messageLength);
    writeInt(blob, 0, 0);
    if(API_MSG_generateDocxMessage == "DONE"):
        writeInt(blob, 0, 1);
    writeInt(blob, 4, messageLength);
    writeString(blob, 8, API_MSG_generateDocxMessage);
    return sendBlob(blob);

def DLL_EXPORT_API_generateDocx(request):
    global API_MSG_generateDocxMessage;
    useEnhance = readInt(request.body, 0);
    API_MSG_generateDocxMessage = "collecting responses...";
    document = "";
    global currentOpenProject;
    for i in currentOpenProject.questions:
        document += "\n\nQUESTION\n\n";
        document += i.question;
        document += "\n\nRESPONSE\n\n";
        if(len(i.responses) == 0):
            document += "(no response has been written yet)";
        else:
            document += i.responses[len(i.responses) - 1];
    generatedFile = generateDOCX(deduplicateFinalDocument(createDocumentStructure(document), useEnhance));
    fileSize = len(generatedFile);
    blob = allocateBlob(4 + fileSize);
    writeInt(blob, 0, fileSize);
    writeBlob(blob, 4, generatedFile);
    API_MSG_generateDocxMessage = "DONE";
    return sendBlob(blob);

class ThreadedWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True;

def openServer():
    warnings.filterwarnings("ignore");
    logging.getLogger("django").setLevel(logging.ERROR);
    logging.getLogger("easyocr").setLevel(logging.ERROR);
    djangoSettingsModuleObject = types.ModuleType("DjangoSettings");
    exec(readFile("settings.py"), djangoSettingsModuleObject.__dict__);
    sys.modules["DjangoSettings"] = djangoSettingsModuleObject;
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DjangoSettings");
    django.setup();
    make_server("0.0.0.0", int(os.environ["PORT"]), get_wsgi_application(), server_class=ThreadedWSGIServer).serve_forever();

def DLL_EXPORT_startServerAndClient():
    openServer();
