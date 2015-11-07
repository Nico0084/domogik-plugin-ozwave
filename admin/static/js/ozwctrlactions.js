/* Library fir zwave controller action */
var RunningCtrlAction ={};
var ListeningStateCtrl = false;
var DialogInit = false;
var Action = {action: 'undefine', cmd: 'undefine', cmdsource: 'undefine', cptmsg: 0, nodeid: 0, highpower:'False' , arg :{}, id: 0};
//var InterListening = setInterval(listeningCtrlState, 17000);
var lastActionSelect =''

var AvaillableCtrlActions = [];

//    ['None','AddDevice', 'AddController' , 'CreateNewPrimary', 'ReceiveConfiguration', 'RemoveDevice', 'RemoveController ', 'RemoveFailedNode', 'HasNodeFailed',
//            'ReplaceFailedNode', 'TransferPrimaryRole', 'RequestNetworkUpdate', 'RequestNodeNeighborUpdate', 'AssignReturnRoute',
//            'DeleteAllReturnRoutes', 'SendNodeInformation', 'ReplicationSend', 'CreateButton', 'DeleteButton'];

function renderActionOption(action) {
    $('#dosecurityOpt').hide();
    $('#listnodesOpt').hide();
    $('#listnodesOptLabel').hide();
    $('#infoOpt').hide();
    $('#numberOpt').hide();
    $('#numberOptLabel').hide();
    switch (action) {
        case 'AddDevice' :
            $('#dosecurityOpt').show();
            break;
        case 'AddController' :
            break;
        case 'RemoveController ' :
            break;
        case 'RemoveDevice' :
            break;
        case 'CreateNewPrimary' :
        case 'ReceiveConfiguration' :
        case 'TransferPrimaryRole' :
            break;
        case 'RequestNodeNeighborUpdate':
        case 'RequestNetworkUpdate' :
            $("#listnodesOpt option[value!='']").remove();
            for (n in nodesData) {
                $('#listnodesOpt').append("<option value='"+ nodesData[n].NodeID +"'>" + renderNodeName(nodesData[n]) + "</option>");
            };
            $('#listnodesOptLabel').show();
            $('#listnodesOpt').show();
            break;
        case 'AssignReturnRoute' :
            $("#listnodesOpt option[value!='']").remove();
            for (n in nodesData) {
                $('#listnodesOpt').append("<option value='"+ nodesData[n].NodeID +"'>" + renderNodeName(nodesData[n]) + "</option>");
            };
            $('#listnodesOptLabel').show();
            $('#listnodesOpt').show();
            // Actualy only route to controller
            $('#infoOpt').text('Return route is assigned to primary controller.(for momment only this possibilty)').show();
            break;
        case 'SendNodeInformation' :
        case 'DeleteAllReturnRoutes' :
            $("#listnodesOpt option[value!='']").remove();
            for (n in nodesData) {
                $('#listnodesOpt').append("<option value='"+ nodesData[n].NodeID +"'>" + renderNodeName(nodesData[n]) + "</option>");
            };
            $('#listnodesOptLabel').show();
            $('#listnodesOpt').show();
            break;
        case 'ReplicationSend' :
            // TODO: check in openzwave what is real action perhaps an issue ?
            $("#listnodesOpt option[value!='']").remove();
            for (n in nodesData) {
                if (nodesData[n].InitState != 'Out of operation') {
                    $('#listnodesOpt').append("<option value='"+ nodesData[n].NodeID +"'>" + renderNodeName(nodesData[n]) + "</option>");
                };
            };
            $('#listnodesOptLabel').show();
            $('#listnodesOpt').show();
            $('#infoOpt').text('Developer information: WARNING, unsure of the real action of the openzwave library.').show();
            break;
        case 'ReplaceFailedNode' :
        case 'RemoveFailedNode' :
            $("#listnodesOpt option[value!='']").remove();
            for (n in nodesData) {
                if (nodesData[n].InitState == 'Out of operation') {
                    $('#listnodesOpt').append("<option value='"+ nodesData[n].NodeID +"'>" + renderNodeName(nodesData[n]) + "</option>");
                };
            };
            $('#listnodesOptLabel').show();
            $('#listnodesOpt').show();
            break;
        case 'HasNodeFailed' :
            $("#listnodesOpt option[value!='']").remove();
            for (n in nodesData) {
                $('#listnodesOpt').append("<option value='"+ nodesData[n].NodeID +"'>" + renderNodeName(nodesData[n]) + "</option>");
            };
            $('#listnodesOptLabel').show();
            $('#listnodesOpt').show();
            break;
        case 'DeleteButton' :
        case 'CreateButton' :
            // TODO: Probably we must check if button allready exist for node.
            $("#listnodesOpt option[value!='']").remove();
            for (n in nodesData) {
                if (nodesData[0].InitState != 'Out of operation') {
                    $('#listnodesOpt').append("<option value='"+ nodesData[n].NodeID +"'>" + renderNodeName(nodesData[n]) + "</option>");
                };
            };
            $('#listnodesOptLabel').show();
            $('#listnodesOpt').show();
            $('#numberOptLabel').text('Button ID').show();
            $('#numberOpt').attr('title', 'Chose a button ID number (1 to 255)').show();
            break;

        default :
    };
};

function renderStateAction (action, state, msg) {
    var icon = "";
    var statusText = state;
    var stop = false;
    switch (state) {
        case "Normal" :
            icon = "fa-circle-o icon-info";
            statusText = "Ready";
            break;
        case 'Starting' :
            icon = "fa-cog icon-success";
            var stop = true;
            break;
        case 'Cancel' :
            icon = "fa-times-circle icon-warning";
            break;
        case 'Error' :
            icon = "fa-exclamation-triangle icon-error";
            break;
        case 'Waiting' :
            icon = "fa-hourglass-o icon-info";
            var stop = true;
            break;
        case 'Sleeping' :
            icon = "fa-pause icon-info";
            var stop = true;
            break;
        case 'InProgress' :
            icon = "fa-cog fa-spin icon-info";
            var stop = true;
            break;
        case 'Completed' :
            icon = "fa-check-square icon-success";
            break;
        case 'Failed' :
            icon = "fa-exclamation-circle icon-error";
            break;
        case 'NodeOK' :
            icon = "fa-check-circle icon-success";
            break;
        case 'NodeFailed' :
            icon = "fa-exclamation-circle icon-error";
            break;
        default :
            icon = "fa-question icon-warning";
    };
    if (stop) {
        $('#btctrlaction-ic').removeClass().addClass("fa fa-stop").attr("style", "color:red");
        $('#btctrlaction-text').text(" Stop action");
        $('.actdisable').attr('disabled', true);
        $('#forcestopaction').hide();
    } else {
        $('#btctrlaction-ic').removeClass().addClass("fa fa-play").attr("style", "color:green");
        $('#btctrlaction-text').text(" Start action");
        $('.actdisable').attr('disabled', false);
        $('#actionmessage').text('');
        $('#actionmessage').hide();
        if (state == 'Error') { $('#forcestopaction').show();
        } else {$('#forcestopaction').hide();};
    };
    $('#actionstatus-ic').removeClass().addClass("fa fa-2x "+icon);
    $('#actionstatus').text("  "+ statusText);
    $('#lastaction').text(action);
    $('#actionresult-ic').removeClass().addClass("fa fa-2x "+icon);
    $('#actionresult').text(msg);
};
