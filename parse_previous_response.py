def filterInfo(s):
    return runAgent(
        "Information Relevance Check",
        """
You are working at Prompta AI, a company that uses AI technology to analyse and improve business practises of partnering organisations who are mostly Canadian government agencies and corporations.
        """,
        """
You are provided with information from a RFP (Request For Proposal) response written by Prompta AI employees. Prompta AI is building a database of RFP responses and your job is to identify the appendices section in each RFP response which would be omitted from the database.
        """,
        """
You are provided with a list of "section headers" from the RFP response. The algorithm for detecting sections headers used is very primitive and only checks for bold text, so most of the "section headers" are likely inaccurate. Each "section header" is presented in the following form:
SECTION[header number] [header text]

example:
SECTION0 General Information

Remember that most of these are likely to be just regular bold text.

Your job is to identify the section header that marks the start of the appendices section. You are to follow this reasoning process:

1. find a section header that is likely the start of the appendices, note that the appendices section can be called something else, such as "additional information"
2. check if it is likely to actually mark the start of the appendices section by looking at "section headers" around it. if it appears extremely early in the document, it is likely part of the contents table and not the actual section. if it is followed by a large amount of non essential or highly specific information, it is likely to be the actual section. if you believe the section header you chose is likely not the start of the appendices, go back to step 1 and look at another section header. Otherwise, output APPEND_START[header number] (example: APPEND_START0) and end your response.

List of section headers provided below:
{section_headers}
        """,
        """
Use a short paragraph to reason about and evaluate different section headers that might be the start of the appendices. Once you found what you are looking for, use another paragraph to reason about section headers around it for confirmation. If you believe you found the correct one, output

APPEND_START[header number]

on a new line.
        """,
        {"section_headers": s},
        False
    );

def getAppendixStartSection(response):
    index = response.find("APPEND_START");
    index += 12;
    s = "";
    while(index < len(response) and response[index] >= '0' and response[index] <= '9'):
        s += response[index];
        index += 1;
    i = 0;
    try:
        i = int(s);
    except:
        i = -1;
    return i;
    
def filterTopLevelHeaders(s):
    return runAgent(
        "Information Classifier",
        """
You are working at Prompta AI, a company that uses AI technology to analyse and improve business practises of partnering organisations who are mostly Canadian government agencies and corporations.
        """,
        """
You are provided with information from a RFP (Request For Proposal) response written by Prompta AI employees. Prompta AI is building a database of RFP responses and your job is to split the RFP response into sections to be processed separately
        """,
        """
You are provided with a list of "section headers" from the RFP response. The algorithm for detecting sections headers used is very primitive and only checks for bold text, so most of the "section headers" are likely inaccurate.Each "section header" is presented in the following form:
SECTION[header number] [header text]

example:
SECTION0 General Information

Remember that most of these are likely to be just regular bold text.

Your job is to identify top level sections headers. The algorithm detects subheaders inside a section but that is not desired in the database. Top level section headers refer to those that match criteria in the RFP received by Prompta AI, and they tend to follow a structured system of index numbers. Anything that is indexed is considered a top level level header (including 1.1.2.3, 1.3, etc)

You are to follow the following thinking process:
1. look through all the section headers and infer the indexing scheme present in the original RFP. Note that the index numbers may be prefixed by one or a few letters. Also not all index numbers may be present because the corresponding RFP sections may not need to be addressed in the RFP response.
2. look through all the section headers again and find section headers that match the indexing scheme. You can refer to section headers by their header numbers.
3. for each section header that you have identified in 2, look at its format again to confirm that it is actually a top level section
4. when step 3 has been done for all potential top level sections identified in step 2, output their tags in order separated by spaces, but before outputting the tags, first output FINAL_ANSWER (example: FINAL_ANSWER SECTION0 SECTION2 SECTION25 SECTION100 SECTION101)

List of section headers provided below:
{section_headers}
        """,
        """
Use a short paragraph in step 1 to reason about the indexing scheme used in the original RFP. To describe it rigorously, you may consider using a regexp. Use another short paragraph in step 2 to identify section headers that have index numbers (and thus are potentially top level sections) matching the format you found in step 1. Then for every section header in step 2, write one or two sentence describing its format and confirm that it matches the format you found in step. For the final step, output FINAL_ANSWER followed by a space separated list of section tags corresponding to what you identified to be top level sections.
        """,
        {"section_headers": s},
        False
    );

def errorTolerantParseToNumber(sectionString):
    numberString = "";
    for i in sectionString:
        if(i >= '0' and i <= '9'):
            numberString += i;
    if(numberString == ""):
        return -1;
    return int(numberString);

def parseSectionsListResponse(response):
    sectionsList = [];
    i = len(response) - 1;
    while(i > 0):
        if(response[i] == 'F' and response[i:i+12:] == "FINAL_ANSWER"):
            response = response[i+12::];
            break;
        i -= 1;
    currentSection = "";
    for i in range(len(response)):
        if(response[i] != ' '):
            currentSection += response[i];
        else:
            currentSectionNumber = errorTolerantParseToNumber(currentSection);
            currentSection = "";
            if(currentSectionNumber != -1):
                sectionsList.append(currentSectionNumber);
    if(currentSection != ""):
        currentSectionNumber = errorTolerantParseToNumber(currentSection);
        if(currentSectionNumber != -1):
            sectionsList.append(currentSectionNumber);
    return sectionsList;

def getNonAppendixSections(fileBlob, isPDF):
    global API_MSG_uploadResponseMessage;
    s = "";
    getSectionsFromDocument(fileBlob, isPDF, False);
    global CACHE_documentSections;
    list = CACHE_documentSections.copy();
    for i in range(len(list)):
        s += ("SECTION" + str(i) + " " + list[i].header + '\n');
    appendixStart = -1;
    tryCount = 0;
    relevantSections = [];
    API_MSG_uploadResponseMessage = "removing unnecessary information...";
    while(appendixStart == -1):
        appendixStart = getAppendixStartSection(filterInfo(s));
        tryCount += 1;
        if(tryCount > 5):
            break;
    for i in range(appendixStart):
        relevantSections.append(list[i]);
    s = "";
    for i in range(len(relevantSections)):
        s += ("SECTION" + str(i) + " " + relevantSections[i].header + '\n');
    API_MSG_uploadResponseMessage = "organising information...";
    sectionsList = parseSectionsListResponse(filterTopLevelHeaders(s));
    sectionsList.append(len(relevantSections));
    output = [];
    i = 0;
    while(i < len(sectionsList) - 1):
        j = sectionsList[i];
        sectionText = relevantSections[sectionsList[i]].text;
        j += 1;
        while(j < sectionsList[i+1]):
            sectionText += ('\n' + relevantSections[j].header + '\n' + relevantSections[j].text);
            j += 1;
        output.append(Section(relevantSections[sectionsList[i]].header, sectionText));
        i += 1;
    return output;

def sortInfo(responseSection):
    return runAgent(
        "Information Categoriser",
        """
You are working at Prompta AI, a company that uses AI technology to analyse and improve business practises of partnering organisations who are mostly Canadian government agencies and corporations.
        """,
        """
You are skilled in reading, understanding, and classifying text, especially those found in the RFP (Request for proposal) responses written by Prompta AI employees. Your job is to determine if each response concerns all employees and if each point could be reused in future RFP response proposals.
        """,
        """
You are provided with a section from a RFP proposal response sent out by Prompta AI:

{section}

Read through the section and answer the 6 questions below, for (a) and (b) write a short paragraph, and for (c) and (d) reply with either YES or NO.
(a): Who does this response concern? Does it concern Prompta AI as a whole or is it only about specific Prompta AI employees?
(b): Can the response be reused in future RFP responses? Is it specific to this RFP, this client, or this project? Responses that include deadlines and specific tasks are very likely specific to this project.
(c): Does this response concern only 1 or a few Prompta AI employees? Use your part (a) answer to answer this.
(d): Is this response specific to only this RFP / client / project? Use your part (b) answer to answer this.
        """,
        """
reply in the following format

(a) [your short paragraph response to (a)]

(b) [your short paragraph response to (b)]

(c) [your YES / NO response to (c)]

(d) [your YES / NO response to (d)]

Note that the response to each part can occupy at most 1 line (no newlines inside).
        """,
        {"section" : responseSection},
        False
    );

def evaluateSortInfoResponse(response, part):
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

lockSortInformation = threading.Lock();
totalLengthSortInformation = 0;
processedLengthSortInformation = 0;
def sortSingleInformation(info):
    output = "";
    for i in range(3):
        response = sortInfo(info);
        if(evaluateSortInfoResponse(response, "(c)") == -1 or evaluateSortInfoResponse(response, "(d)") == -1):
            if(i == 2):
                output = "0" + info;
                break;
        elif(evaluateSortInfoResponse(response, "(c)") == 0 and evaluateSortInfoResponse(response, "(d)") == 0):
            output = "1" + info;
            break;
        else:
            output = "0" + info;
            break;
    global lockSortInformation;
    global totalLengthSortInformation;
    global processedLengthSortInformation;
    lockSortInformation.acquire();
    processedLengthSortInformation += 1;
    global API_MSG_uploadResponseMessage;
    API_MSG_uploadResponseMessage = "checking relevance..." + str(int(100.0 * float(processedLengthSortInformation) / float(totalLengthSortInformation))) + "%";
    lockSortInformation.release();
    return output;

def sortInformation(list, reuse, noReuse):
    global API_MSG_uploadResponseMessage;
    API_MSG_uploadResponseMessage = "checking relevance...";
    global totalLengthSortInformation;
    global processedLengthSortInformation;
    totalLengthSortInformation = len(list);
    processedLengthSortInformation = 0;
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = [];
        for i in list:
            futures.append(executor.submit(sortSingleInformation, i));
        for f in futures:
            result = f.result();
            if(result != "" and result[0] == '1'):
                reuse.append(result[1::]);
            else:
                noReuse.append(result[1::]);

def sortInfoInDocument(fileBlob, isPDF, reuse, noReuse):
    destructuredSectionsList = [];
    list = getNonAppendixSections(fileBlob, isPDF);
    for section in list:
        destructuredSectionsList.append(section.header + "\n" + section.text);
    sortInformation(destructuredSectionsList, reuse, noReuse);

def parseListOfPoints(pointsList):
    list = [];
    s = "";
    pointsList = cleanLeadingTrailingSpace(pointsList);
    if(pointsList[len(pointsList)-10:10:] == "NO_CONTENT"):
        return [];
    pointsList += '\n';
    for i in range(len(pointsList)):
        if(pointsList[i] == '\n'):
            if(cleanLeadingTrailingSpace(s) != ""):
                list.append(cleanLeadingTrailingSpace(s));
                s = "";
        else:
            s += pointsList[i];
    return list;

lockGetPoints = threading.Lock();
totalLengthGetPoints = 0;
processedLengthGetPoints = 0
def getPoints(responseSection):
    response = runAgent(
        "Information Summariser",
        """
You are working at Prompta AI, a company that uses AI technology to analyse and improve business practises of partnering organisations who are mostly Canadian government agencies and corporations.
        """,
        """
You are skilled in reading, understanding, and summarising text, especially those found in the RFP (Request for proposal) responses written by Prompta AI employees. Your job is to divide the information in a section of a RFP response into a bullet point list.
        """,
        """
You are provided with a section from a RFP proposal response sent out by Prompta AI:

{section}

Rewrite the section into a bullet point list according to the following criteria
- any independent piece of information in the section should have its own point
- information that does not concern the Prompta AI company should be omitted
- every point should be self contained, this means that it can be read without context from other points in the list
- there should not be nested points
- do not split quotations into multiple points, also include the quotation author in the point if it is a quotation

Note that section may not be properly formatted. Even if that is the case, your response must be properly formatted. If the section content is not provided, output NO_CONTENT at the end of your response.
        """,
        """
Present your output in a bullet point list, each point should be on its own line. Points cannot occupy more than 1 line (no newline inside a point). Use a dash - as the bullet point.
        """,
        {"section" : responseSection},
        False
    );
    global lockGetPoints;
    global totalLengthGetPoints;
    global processedLengthGetPoints;
    lockGetPoints.acquire();
    processedLengthGetPoints += 1;
    global API_MSG_uploadResponseMessage;
    API_MSG_uploadResponseMessage = "formatting extracted points... " + str(int(100.0 * float(processedLengthGetPoints) / float(totalLengthGetPoints))) + "%";
    lockGetPoints.release();
    return parseListOfPoints(response);

def parsePreviousResponse(fileBlob, isPDF):
    global API_MSG_uploadResponseMessage;
    canReusePoints = [];
    cannotReusePoints = [];
    sortInfoInDocument(fileBlob, isPDF, canReusePoints, cannotReusePoints);
    canReuse = [];
    global totalLengthGetPoints;
    global processedLengthGetPoints;
    API_MSG_uploadResponseMessage = "formatting extracted points... ";
    totalLengthGetPoints = len(canReusePoints);
    processedLengthGetPoints = 0;
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = [];
        for i in canReusePoints:
            futures.append(executor.submit(getPoints, i));
        for f in futures:
            canReuse.extend(f.result());
    return canReuse;

def deduplicate(info):
    return runAgent(
        "Information Summariser",
        """
You are working at Prompta AI, a company that uses AI technology to analyse and improve business practises of partnering organisations who are mostly Canadian government agencies and corporations.
        """,
        """
You are skilled in reading, understanding, and summarising text, especially those found in the RFP (Request for proposal) responses written by Prompta AI employees. Your job is to tidy a database by removing duplicate information.
        """,
        """
You will be provided with information in the form of a bullet point list from a company database used for writing RFP response proposals. Rewrite the information into a bullet point list according to the following criteria
- any independent piece of information in the section should have its own point
- information that does not concern the Prompta AI company should be omitted
- every point should be self contained, this means that it can be read without context from other points in the list
- there should not be nested points
- do not split quotations into multiple points, also include the quotation author in the point if it is a quotation
- if there are multiple existing points that convey a similar meaning, keep only 1 copy of the point
- if there are multiple existing points that contain overlapping content, summarise them into 1 point
- if there are points that contradict each other, keep only the one found later in the list
- as much as possible, avoid changing the order of points in the list

Note that information may not be properly formatted. Even if that is the case, your response must be properly formatted.

The information is provided below:

{info}
        """,
        """
Present your output in a bullet point list, each point should be on its own line. Points cannot occupy more than 1 line (no newline inside a point). Use a dash - as the bullet point.
        """,
        {"info" : info},
        False
    );

def DLL_EXPORT_addPreviousResponseToDataBase(fileBlob, isPDF):
    global API_MSG_uploadResponseMessage;
    databaseInfo = readFile("database.txt");
    list = parsePreviousResponse(fileBlob, isPDF);
    for i in list:
        databaseInfo += (i + '\n');
    API_MSG_uploadResponseMessage = "completing database modifications...";
    databaseInfo = deduplicate(databaseInfo);
    writeFile("database.txt", databaseInfo);
    API_MSG_uploadResponseMessage = "DONE";

def aiEditDatabaseContents(instructions, databaseInfo):
    return runAgent(
        "Database Maintainer",
        """
You are working at Prompta AI, a company that uses AI technology to analyse and improve business practises of partnering organisations who are mostly Canadian government agencies and corporations.
        """,
        """
You are skilled in reading, understanding, and summarising text, especially those found in the RFP (Request for proposal) responses written by Prompta AI employees. Your job is to tidy a database according to provided instructions.
        """,
        """
You will be provided with information in the form of a bullet point list from a company database used for writing RFP response proposals. You will also be provided with instructions below. Modify the database according to the instructions below. The instructions may ask you to remove mentions of something in the database or to rephrase information.

Instructions:
{instructions}

Existing information in database:
{database}
        """,
        """
Present your output in a bullet point list, each point should be on its own line. Points cannot occupy more than 1 line (no newline inside a point). Use a dash - as the bullet point. Your output will be directly used as the new database.
        """,
        {
            "instructions": instructions,
            "database": databaseInfo
        },
        False
    );

def DLL_EXPORT_editDatabaseContents(instructions):
    databaseInfo = readFile("database.txt");
    databaseInfo = aiEditDatabaseContents(instructions, databaseInfo);
    writeFile("database.txt", databaseInfo);
