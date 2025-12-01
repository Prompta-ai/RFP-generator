from django.urls import path;

exec(open("utilities.py").read());
staticLink("get_sections.py");
staticLink("parse_incoming_RFP.py");
staticLink("parse_previous_response.py");
staticLink("write_response.py");
staticLink("start_server.py");

urlpatterns = [
    path("", getJSMainFunction),
    path("projects", DLL_EXPORT_API_readProjectList),
    path("new_project", DLL_EXPORT_API_createNewProject),
    path("new_project_sample", DLL_EXPORT_API_respondProjectCreationSample),
    path("upload_response", DLL_EXPORT_API_uploadResponse),
    path("upload_response_sample", DLL_EXPORT_API_uploadResponseSample),
    path("generate_docx", DLL_EXPORT_API_generateDocx),
    path("generate_docx_sample", DLL_EXPORT_API_generateDocxSample),
    path("open_project", DLL_EXPORT_API_openProject),
    path("get_question", DLL_EXPORT_API_getQuestion),
    path("save_response", DLL_EXPORT_API_saveResponse),
    path("revert_response", DLL_EXPORT_API_revertResponse),
    path("generate", DLL_EXPORT_API_generateResponse),
    path("enhance", DLL_EXPORT_API_enhanceResponse),
    path("get_database", DLL_EXPORT_API_getDatabase),
    path("set_database", DLL_EXPORT_API_setDatabase),
    path("get_requirements", DLL_EXPORT_API_getRequirements),
    path("set_requirements", DLL_EXPORT_API_setRequirements),
    path("get_general_info", DLL_EXPORT_API_getGeneralInfo),
    path("set_general_info", DLL_EXPORT_API_setGeneralInfo),
    path("delete_project", DLL_EXPORT_API_deleteProject),
    path("terminate_with_save", DLL_EXPORT_API_terminateWithSave),
    path("terminate_server", DLL_EXPORT_API_terminateServer),
    path("ignore_rfp_response", DLL_EXPORT_API_receiveIgnoreRFPInterruptResponse),
    path("database_edit", DLL_EXPORT_API_editDatabaseContents)
]
