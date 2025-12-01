import threading;
from concurrent.futures import ThreadPoolExecutor, as_completed;

RawQuestion = namedtuple("RawQuestion", ["question", "automatable"]);

def summariseSection(section):
    return runAgent(
        "Proposal Analyst",
        """
You are working at Prompta AI, a company that uses AI technology to analyse and improve business practises of partnering organisations who are mostly Canadian government agencies and corporations.
        """,
        """
You are an experienced proposal analyst at Prompta AI, specialising in reading complex RFPs from corporations and government agencies. Your current job is to extract from a RFP sections that will be helpful to the response proposal writing team.
        """,
        """
You are provided with a section of a RFP (request for proposal) received by Prompta AI. This is not the full RFP, only a section of it. The section may or may not contain questions to be addressed in the written response proposal. You should analyse the section, write a short summary of what it concerns (general information, written proposal, presentation, interview, etc), and decide on if it contains the questions to be answered in the written proposal. You may disregard all other information including general information provided and information that concerns only the presentation and interview.

Below is the provided RFP section:

{section}
        """,
        "A short summary of the section that focuses on what the section concerns, followed by a 1 word answer, YES or NO, that indicates if the section contains questions that should be addressed in the written proposal",
        {"section": (section.header + "\n" + section.text)},
        False
    );

lockProcessSection = threading.Lock();
totalLengthProcessSection = 0;
processedLengthProcessSection = 0;
def processSection(section):
    output = "";
    for i in range(3):
        response = summariseSection(section);
        if(len(response) > 2 and response[len(response) - 2::] == "NO"):
            output = "";
            break;
        if(len(response) > 3 and response[len(response) - 3::] == "YES"):
            output = (section.header + "\n" + section.text + "\n\n");
            break;
        if(i == 2):
            output = "INVALID";
    global lockProcessSection;
    global totalLengthProcessSection;
    global processedLengthProcessSection;
    lockProcessSection.acquire();
    processedLengthProcessSection += 1;
    global API_MSG_projectCreationMessage;
    API_MSG_projectCreationMessage = "finding questions to respond to... " + str(int(100.0 * float(processedLengthProcessSection) / float(totalLengthProcessSection))) + "%";
    lockProcessSection.release();
    return output;

def summariseRFP():
    global CACHE_documentSections;
    list = CACHE_documentSections.copy();
    errorCode = 0;
    output = "";
    global totalLengthProcessSection;
    global processedLengthProcessSection;
    global API_MSG_projectCreationMessage;
    API_MSG_projectCreationMessage = "finding questions to respond to...";
    totalLengthProcessSection = len(list);
    processedLengthProcessSection = 0;
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = [];
        for i in list:
            futures.append(executor.submit(processSection, i));
        for f in futures:
            result = f.result();
            if(result == "INVALID"):
                errorCode = 1;
                break;
            output += result;
    if(errorCode == 1):
        return "INVALID";
    else:
        return output;

def getQuestions(rfpSummary):
    global API_MSG_projectCreationMessage;
    API_MSG_projectCreationMessage = "looking for additional requirements...";
    return runAgent(
        "Proposal Analyst",
        """
You are working at Prompta AI, a company that uses AI technology to analyse and improve business practises of partnering organisations who are mostly Canadian government agencies and corporations.
        """,
        """
You are an experienced proposal analyst at Prompta AI, specialising in reading complex RFPs from corporations and government agencies. Your current job is to extract from a few RFP sections a list of items that must be included inside or with Prompta AI's response proposal to the RFP.
        """,
        """
You are provided with a section of a RFP (request for proposal) received by Prompta AI. This is not the full RFP, only a section of it. From this section, you must extract a list of items that Prompta AI's response proposal should include. This can include answers to questions, forms for submission, and attachments requested in the RFP. You may disregard all other information including general information provided and information that concerns only the presentation and interview. It is important that the list is linear (no nested points) and every point is self-contained (does not reference other points). Additional information relevant to answering the questions, such as page count limits, pricing requirements etc should be included in a separate list in the ADDITIONAL_REQUIREMENTS section.

Below is the provided RFP section:

{section}
        """,
        "2 sections, DELIVERABLES and ADDITIONAL_REQUIREMENTS. The DELIVERABLES section should contain a bullet point list of items to be included within or attached to Prompta AI's response RFP. The ADDITIONAL_REQUIREMENTS section should contain a bullet point list of additional information to be taken note of when answering the questions. For both lists, each point should occupy exactly 1 line (no newlines inside points) and use a dash - as bullet point.",
        {"section" : rfpSummary},
        False
    );

def attachInfo(questionListNoInfo):
    global API_MSG_projectCreationMessage;
    API_MSG_projectCreationMessage = "understanding additional requirements...";
    return runAgent(
        "Proposal Analyst",
        """
You are working at Prompta AI, a company that uses AI technology to analyse and improve business practises of partnering organisations who are mostly Canadian government agencies and corporations.
        """,
        """
You are an experienced proposal analyst at Prompta AI, specialising in reading complex RFPs from corporations and government agencies. Someone else has read through a RFP received by Prompta and extracted the list of questions. Your job now is to process the questions into independent points.
        """,
        """
You are provided with a list of questions extracted from a RFP which includes everything that must be mentioned in Prompta AI's written response proposal. There are 2 parts to the list, DELIVERABLES and ADDITIONAL_REQUIREMENTS. Every point in the DELIVERABLES section is a part that must be included in the RFP and the ADDITIONAL_REQUIREMENTS section is additional instructions that must be followed when writing the response proposal.

Below is the provided list of questions:

{section}

You are to attach additional requirements to each question by evaluating if it is relevant to answer that specific question. If multiple questions are very closely interconnected or follow from each other, you may merge them into 1 question. It is important that the list of questions is linear (no nested points) and every point is self-contained (does not reference other points, but can reference RFP sections).
        """,
        """
a list of questions that correspond to the original DELIVERABLE section. Within each item of the list, have a bullet point list with 1 point per piece of relevant additional information. Separate different questions by 2 newlines. No sections headers are needed. Each question and its points should make sense by itself without the other questions, so make changes such as "for every example" to "for every past project proposed" if suitable in context.

Sample format
-----
[question 1]
- [relevant requirement 1]
- [relevant requirement 2]

[question 2]

[question 3]
- [relevant requirement 1]

etc
        """,
        {"section" : questionListNoInfo},
        False
    );

def sortQuestion(questionWithInfo):
    return runAgent(
        "Proposal Analyst",
        """
You are working at Prompta AI, a company that uses AI technology to analyse and improve business practises of partnering organisations who are mostly Canadian government agencies and corporations.
        """,
        """
You are an experienced proposal analyst at Prompta AI, specialising in reading complex RFPs from corporations and government agencies. Prompta AI has previously received a RFP and has processed it to extract the points that must be mentioned in the written response proposal. Your job is to determine if each point concerns all employees and if each point concerns the current RFP.
        """,
        """
You are provided with information about a section that must be present in Prompta AI's response written proposal below:

{section}

Read through the section requirements and answer the 4 questions below, for (a) and (b) write a short paragraph, and for (c) and (d) reply with either YES or NO.
(a): Who does this question concern? Does it concern Prompta AI as a whole or is it only asking about specific Prompta AI employees?
(b): Can the response to this question be reused in response proposals to RFPs received in future? Is it specific to this RFP?
(c): Does this question concern only 1 or a few Prompta AI employees? Use your part (a) answer to answer this.
(d): Is this question specific to only this RFP? Use your part (b) answer to answer this.
        """,
        """
reply in the following format

(a) [your short paragraph response to (a)]

(b) [your short paragraph response to (b)]

(c) [your YES / NO response to (c)]

(d) [your YES / NO response to (d)]

Note that the response to each part can occupy at most 1 line (no newlines inside).
        """,
        {"section" : questionWithInfo},
        False
    );

def evaluateSortResponse(response, part):
    index = response.find(part);
    if(index == -1):
        return -1;
    prevNewline = index;
    nextNewline = index;
    while(prevNewline >= 0):
        if(response[prevNewline] == '\n'):
            break;
        prevNewline -= 1;
    while(nextNewline < len(response)):
        if(response[nextNewline] == '\n'):
            break;
        nextNewline += 1;
    response = response[prevNewline + 1:nextNewline:];
    if(response.find("YES") != -1):
        return 1;
    elif(response.find("NO") != -1):
        return 0;
    return -1;

lockSortQuestion = threading.Lock();
totalLengthSortQuestion = 0;
processedLengthSortQuestion = 0;
def sortSingleQuestion(question):
    j = 0;
    output = "";
    while(j < 3):
        response = sortQuestion(question);
        if(evaluateSortResponse(response, "(c)") == -1 or evaluateSortResponse(response, "(d)") == -1):
            if(j >= 3):
                output = "0" + question;
                break;
        elif(evaluateSortResponse(response, "(c)") == 0 and evaluateSortResponse(response, "(d)") == 0):
            output = "1" + question;
            break;
        else:
            output = "0" + question;
            break;
    global lockSortQuestion;
    global totalLengthSortQuestion;
    global processedLengthSortQuestion;
    lockSortQuestion.acquire();
    processedLengthSortQuestion += 1;
    global API_MSG_projectCreationMessage;
    API_MSG_projectCreationMessage = "classifying questions... " + str(int(100.0 * float(processedLengthSortQuestion) / float(totalLengthSortQuestion))) + "%";
    lockSortQuestion.release();
    return output;

def sortQuestions(questions):
    output = [];
    list = stringToList(questions);
    global totalLengthSortQuestion;
    global processedLengthSortQuestion;
    global API_MSG_projectCreationMessage;
    API_MSG_projectCreationMessage = "classifying questions...";
    totalLengthSortQuestion = len(list);
    processedLengthSortQuestion = 0;
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = [];
        for i in list:
            futures.append(executor.submit(sortSingleQuestion, i));
        for f in futures:
            result = f.result();
            if(result == ""):
                continue;
            elif(result[0] == '0'):
                output.append(RawQuestion(result[1::], False));
            elif(result[0] == '1'):
                output.append(RawQuestion(result[1::], True));
    return output;

def summariseSectionForInfo(section):
    return runAgent(
        "Proposal Analyst",
        """
You are working at Prompta AI, a company that uses AI technology to analyse and improve business practises of partnering organisations who are mostly Canadian government agencies and corporations.
        """,
        """
You are an experienced proposal analyst at Prompta AI, specialising in reading complex RFPs from corporations and government agencies. Your current job is to extract from a RFP information that indicate the general topic of a project.
        """,
        """
You are provided with a section of a RFP (request for proposal) received by Prompta AI. This is not the full RFP, only a section of it. The section may or may not contain information that you are looking for. You should analyse the section, write a short summary of what it concerns (general information, written proposal, presentation, interview, etc), and decide on if it contains the information that you want.

You are looking for information that indicate the general field (change management, employee survey, inclusivity audit etc) of the project. You may consider overly specific information such as deadlines and personnel requirements as irrelevant. For this purpose, any information about the preparation for, requirements of, and evaluation of RFP responses is irrelevant, this includes information about what the RFP response proposal should address and submission deadlines. However, sections dedicated to providing information about what Prompta AI has to do if the project is started are always considered relevant. For other sections, a section is relevant if at least 75% of the information contained is relevant.

Below is the provided RFP section:

{section}
        """,
        "A short summary of the section that focuses on what the section concerns and analysis of if the section is considered relevant, followed by a 1 word answer, YES or NO, that indicates if the section is relevant based on your summary. There should not be anything after the YES / NO choice",
        {"section": (section.header + "\n" + section.text)},
        False
    );

lockProcessSectionForInfo = threading.Lock();
totalLengthProcessSectionForInfo = 0;
processedLengthProcessSectionForInfo = 0;
def processSectionForInfo(section):
    output = "";
    for i in range(3):
        response = summariseSectionForInfo(section);
        if(len(response) > 2 and response[len(response) - 2::] == "NO"):
            output = "";
            break;
        if(len(response) > 3 and response[len(response) - 3::] == "YES"):
            output = (section.header + "\n" + section.text + "\n");
            break;
        if(i == 2):
            output = "INVALID";
    global lockProcessSectionForInfo;
    global totalLengthProcessSectionForInfo;
    global processedLengthProcessSectionForInfo;
    lockProcessSectionForInfo.acquire();
    processedLengthProcessSectionForInfo += 1;
    global API_MSG_projectCreationMessage;
    API_MSG_projectCreationMessage = "finding general information... " + str(int(100.0 * float(processedLengthProcessSectionForInfo) / float(totalLengthProcessSectionForInfo))) + "%";
    lockProcessSectionForInfo.release();
    return output;

def summariseRFPForInfo():
    global API_MSG_projectCreationMessage;
    global CACHE_documentSections;
    list = CACHE_documentSections.copy();
    errorCode = 0;
    output = "";
    global totalLengthProcessSectionForInfo;
    global processedLengthProcessSectionForInfo;
    global API_MSG_projectCreationMessage;
    API_MSG_projectCreationMessage = "finding general information...";
    totalLengthProcessSectionForInfo = len(list);
    processedLengthProcessSectionForInfo = 0;
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = [];
        for i in list:
            futures.append(executor.submit(processSectionForInfo, i));
        for f in futures:
            result = f.result();
            if(result == "INVALID"):
                errorCode = 1;
                break;
            output += result;
    if(errorCode == 1):
        return "INVALID";
    else:
        return output;

def summariseGeneralInformation(infoList):
    global API_MSG_projectCreationMessage;
    API_MSG_projectCreationMessage = "summarising general information...";
    return runAgent(
        "Text Summariser",
        """
You are working at Prompta AI, a company that uses AI technology to analyse and improve business practises of partnering organisations who are mostly Canadian government agencies and corporations.
        """,
        """
You are an experienced proposal analyst at Prompta AI, specialising in reading complex RFPs from corporations and government agencies. Your current job is to summarise information extracted from a RFP received by Prompta AI.
        """,
        """
You are provided with information extracted from a RFP received by Prompta AI. You are to summarise the information to make it more consise and remove irrelevant information.

You are looking for information that indicate the general field (change management, employee survey, inclusivity audit etc) of the project. You may consider overly specific information such as deadlines and personnel requirements as irrelevant. For this purpose, any information about the preparation for, requirements of, and evaluation of RFP responses is irrelevant, this includes information about what the RFP response proposal should address and submission deadlines.

Note that the original information may not be formatted correcly. However, make sure to format your response correctly

Original Information extracted from the RFP:

{section}
        """,
        """
A short paragraph focusing on what the provided RFP text tells you about the general topic of the project. You may include minimal explanation and details. All information in your paragraph should be relevant, you may and should remove unimportant information from the original text.
        """,
        {"section": infoList},
        False
    );

def DLL_EXPORT_parseIncomingRFP(questionsList):
    global API_MSG_projectCreationMessage;
    filteredRFP = summariseRFP();
    internalQuestionsList = sortQuestions(attachInfo(getQuestions(filteredRFP)));
    for i in internalQuestionsList:
        questionsList.append(i);
    generalInfo = summariseGeneralInformation(summariseRFPForInfo());
    return generalInfo;

def getQuestionSummary(question):
    return runAgent(
        "Question title writer",
        """
You are working at Prompta AI, a company that uses AI technology to analyse and improve business practises of partnering organisations who are mostly Canadian government agencies and corporations.
        """,
        """
You are an experienced proposal analyst at Prompta AI, specialising in reading complex RFPs from corporations and government agencies. Your current job is to write a title for a RFP requestion received by Prompta AI.
        """,
        """
You are provided with a question from a RFP document received by Prompta AI. You are to write a short title for the question so that employees can know what the question is about without having to read it. The question title should be around 5 words long.

Question extracted from the RFP:
{question}
        """,
        """
An approximately 5 word long title for the question. Do NOT include anything else or offer to help in your response, your response will be used in the database directly.
        """,
        {"question": question},
        False
    );

lockSummariseQuestion = threading.Lock();
totalLengthSummariseQuestion = 0;
processedLengthSummariseQuestion = 0;
def summariseQuestion(question):
    output = getQuestionSummary(question);
    global lockSummariseQuestion;
    global totalLengthSummariseQuestion;
    global processedLengthSummariseQuestion;
    lockSummariseQuestion.acquire();
    processedLengthSummariseQuestion += 1;
    global API_MSG_projectCreationMessage;
    API_MSG_projectCreationMessage = "writing title for questions... " + str(int(100.0 * float(processedLengthSummariseQuestion) / float(totalLengthSummariseQuestion))) + "%";
    lockSummariseQuestion.release();
    return output;

def DLL_EXPORT_summariseQuestions(list):
    global API_MSG_projectCreationMessage;
    API_MSG_projectCreationMessage = "writing title for questions...";
    titleList = [];
    global totalLengthSummariseQuestion;
    global processedLengthSummariseQuestion;
    totalLengthSummariseQuestion = len(list);
    processedLengthSummariseQuestion = 0;
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = [];
        for i in list:
            futures.append(executor.submit(summariseQuestion, i));
        for f in futures:
            result = f.result();
            titleList.append(result);
    return titleList;

def ifSatisfyRequirement(section, requirementsList):
    return runAgent(
        "Proposal Analyst",
        """
You are working at Prompta AI, a company that uses AI technology to analyse and improve business practises of partnering organisations who are mostly Canadian government agencies and corporations.
        """,
        """
You are an experienced proposal analyst at Prompta AI, specialising in reading complex RFPs from corporations and government agencies. Your current job is to determine if Prompta AI should consider responding to a RFP recently received.
        """,
        """
You are provided with a section from the RFP. This is not the full RFP and may not even contain any relevant information at all. You should first write a short summary of any requirements that the section gives. After that,  compare the requirements found in the section with the list of Prompta AI requirements attached below to find all contradicting points (there may be none or more than 1 contradictions).

If there are no contradicting points, write SECTION_IS_OK on a new line. Otherwise, write SECTION_NOT_OK on a new line and immediately after it, write a short paragraph describing which parts of the RFP section contradict which parts of the Prompta AI requirements list.

RFP section:
{section}

Prompta AI RFP requirements:
{requirements}
        """,
        """
A short paragraph outlining requirements defined by the RFP section, followed by a short paragraph comparing the requirements from the RFP section with the requirements from the provided list, followed by
either
(a) the text SECTION_IS_OK if no contradictions are found
or
(b) the text SECTION_NOT_OK followed by a short paragraph explaining the contradictions, if any is found
        """,
        {
            "section": (section.header + "\n" + section.text),
            "requirements": requirementsList
        },
        False
    );

def checkRequirement(section, requirementsList):
    response = ifSatisfyRequirement(section, requirementsList);
    output = "";
    if(response.find("SECTION_IS_OK") != -1):
        output = "";
    elif(response.find("SECTION_NOT_OK") == -1):
        output = response;
    else:
        output = response[response.find("SECTION_NOT_OK")+14::];
    if(output != ""):
        output += "\n\n--------------------------------------------------------\nRFP section here:\n\n" + section.header + "\n" + section.text;
    return output;

lockIgnoreRFPChecks = threading.Lock();
totalLengthIgnoreRFPChecks = 0;
processedLengthIgnoreRFPChecks = 0;
def processIgnoreRFPChecks(section, requirementsList):
    output = checkRequirement(section, requirementsList);
    global lockIgnoreRFPChecks;
    global totalLengthIgnoreRFPChecks;
    global processedLengthIgnoreRFPChecks;
    lockIgnoreRFPChecks.acquire();
    processedLengthIgnoreRFPChecks += 1;
    global API_MSG_projectCreationMessage;
    API_MSG_projectCreationMessage = "checking if should ignore RFP... " + str(int(100.0 * float(processedLengthIgnoreRFPChecks) / float(totalLengthIgnoreRFPChecks))) + "%";
    lockIgnoreRFPChecks.release();
    return output;

def DLL_EXPORT_checkIfIgnore(fileBlob, fileType):
    getSectionsFromDocument(fileBlob, fileType, True);
    global CACHE_documentSections;
    global API_MSG_projectCreationMessage;
    API_MSG_projectCreationMessage = "checking if should ignore RFP...";
    list = CACHE_documentSections.copy();
    requirementsList = readFile("requirements.txt");
    issues = [];
    global totalLengthIgnoreRFPChecks;
    global processedLengthIgnoreRFPChecks;
    totalLengthIgnoreRFPChecks = len(list);
    processedLengthIgnoreRFPChecks = 0;
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = [];
        for i in list:
            futures.append(executor.submit(processIgnoreRFPChecks, i, requirementsList));
        for f in futures:
            result = f.result();
            if(result != ""):
                issues.append(result);
    return issues;
