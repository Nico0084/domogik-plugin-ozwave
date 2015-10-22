var clientID ="";
var ozwInfo;
var nodesData = new Array();  // global list of all nodes whith there data.
// Reference of displaying key node in DataTable nodes column.
var COL_NODE_REF = {"Node": 0, "InitState": 0, "Stage": 0, "BatteryLevel":0, 
                                "Name": 1,
                                "Location": 2,
                                "Model": 3,
                                "State Sleeping": 4,
                                "Type": 5, "Capabilities": 5,
                                "Last update": 6,
                                };
    
var mbrGrpSt = {0: 'unknown', 1: 'confirmed', 2: 'to confirm', 3: 'to update'};

// Handle Data nodes table

function GetNodeRefId(NetworkID, NodeID) {
    return  "_" + NetworkID + "_" + NodeID;
};

function GetValueRefId(NetworkID, NodeID, ValueID) {
    return  "_" + NetworkID + "_" + NodeID + "_" + ValueID;
};

function RefreshDataNode(dataNode, Kbuild) {
    var idx = -1;
    for (var i = 0; i < nodesData.length; i++) {
        if (nodesData[i].NodeID == dataNode.NodeID) {
            idx = i;
            break;
        };
    };
    if (idx != -1) {
        nodesData[idx] = dataNode;
        if (nodesData[idx].ktcNode) {
            nodesData[idx].ktcNode.update();
            };
    } else {
        var d = new Date();
        dataNode.LastReqRefresh = d.getTime();
        nodesData.push(dataNode);
        idx = nodesData.length - 1;
    };
//    if (Kbuild) {
//        if  (initialized) {setTimeout(function () {
//             neighborsGraph.buildKineticNeighbors();
//            },1000);   
//        } else {setTimeout(function () {
//            neighborsGraph = new KtcNeighborsGraph('containerneighbors','graphneighbors');
//            },1000); };
//        initialized = true;
//        };
    return nodesData[idx];
};

function RefreshValuesNodeData(NetworkID, NodeID, Values) {
    for (var i=0; i < nodesData.length; i++) {
        if ((nodesData[i].NodeID == NodeID) && (nodesData[i].NetworkID == NetworkID)) {
                nodesData[i].Values = Values;
            break;
        };
    };
};

function RefreshValueNodeData(NetworkID, NodeID, value) {
    for (var i=0; i < nodesData.length; i++) {
        if ((nodesData[i].NodeID == NodeID) && (nodesData[i].NetworkID == NetworkID)) {
            for (var v=0; v < nodesData[i].Values.length; v++) {
                if (nodesData[i].Values[v].id ==value.id) {
                    nodesData[i].Values[v] = value;
                    break;
                };
            }
            break;
        };
    };
};

function RefreshGroupsNodeData(NetworkID, NodeID, groups) {
    for (var i=0; i < nodesData.length; i++) {
        if ((nodesData[i].NodeID == NodeID) && (nodesData[i].NetworkID == NetworkID)) {
            if (groups[0].index != undefined) {
                nodesData[i].Groups = groups;
            } else {
                var exist = false;
                for (var g=0; g <groups.length; g++) {
                    exist = false;
                    for (var grp=0; grp<nodesData[i].Groups.length; grp++) {
                        if (nodesData[i].Groups[grp].index == groups[g].idx) {
                            nodesData[i].Groups[grp].members = groups[g].mbs;
                            exist = true;
                            break;
                        };
                    };
                    if (!exist) {
                        new PNotify({
                            type: 'error',
                            title: 'Corrupted group association data .',
                            text: 'For node ' + nodesData[i].NetworkID + "." + nodesData[i].NodeID + " groups index " + groups[g].idx + " not exist !",
                            delay: 6000
                        });
                    };
                };
            };
            return nodesData[i];
        };
    };
    return false;
};

function GetValueZWNode(NetworkID, NodeID, ValueID) {
    for (var i=0; i < nodesData.length; i++) {
        if ((nodesData[i].NodeID == NodeID) && (nodesData[i].NetworkID == NetworkID)) {
            if (nodesData[i].Values.length != 0) {
                for (var v=0; v < nodesData[i].Values.length; v++) {
                    if (nodesData[i].Values[v].id ==ValueID) {
                        return nodesData[i].Values[v];
                    };
                };
            } else {
                return false;
            };
        };
    };
    return false;
};

function GetZWNode(NetworkID, NodeID) {
    for (var i=0; i < nodesData.length; i++) {
        if ((nodesData[i].NodeID == NodeID) && (nodesData[i].NetworkID == NetworkID)) {
            return nodesData[i];
        };
    };
    return false;
};

function GetZWNodeByRow(rowCell) {
    try {
        var data = rowCell.data();
        var nodeRef= data.split(".");
        return GetZWNode(nodeRef[0], parseInt(nodeRef[1]));
        }
    catch (err) {
        console.log(err);
        return false;
    }
};

function updateNode(newNodeData, date) {
    var nodeData = GetZWNode(newNodeData.NetworkID, newNodeData.NodeID);
    var table = $("#tabnodes_" + newNodeData.NetworkID).DataTable();
    var keyToUpdate = [];
    if (nodeData) { // Node allready exist in nodesData list
        for (key in newNodeData) { // update or add key
            if (nodeData[key] != newNodeData[key]) {
                nodeData[key] = newNodeData[key];
                keyToUpdate.push(key);
            };
        };
        nodeData = RefreshDataNode(nodeData);
        var nodeTableColUpd = {};
        for (key in keyToUpdate) {
            if (table) {
                var cell = GetNodeCell(table, nodeData.NodeID, COL_NODE_REF[key]);
                if (cell) {
                    if (nodeTableColUpd[COL_NODE_REF[key]] === undefined  || !nodeTableColUpd[COL_NODE_REF[key]] ) {
                        nodeTableColUpd[COL_NODE_REF[key]] = updateNodeTableCell(cell, key, nodeData, date);
                    };
                };
            };
        };
    } else {
        nodeData = RefreshDataNode(newNodeData);
    };
    if (table) {
        var cell = GetNodeCell(table, nodeData.NodeID, 0);
        if (!cell) {
            console.log("Node must be add in nodesData");
            addNodeTableRow(table, nodeData);
        };
    };
};

function sendRequest(request, data, callback) {
    $.getJSON('/plugin_ozwave/' + clientID + '/request/' + request, data, 
        callback);
};

function requestZWNodeInfos(NetworkID, nodeId) {
    if ((NetworkID != undefined) && (nodeId != undefined)) {
        var nodeData = GetZWNode(NetworkID, nodeId);
        var d = new Date();
        if (nodeData) {
            if (nodeData.LastReqRefresh <= d.getTime() + 5000) {
                console.log("Request node infos to close, request abort (NetworkID = " + NetworkID + ", nodeId = " +nodeId + ")");
                return;
            };
        };
        console.log("Requesting node infos, NetworkID = " + NetworkID + ", nodeId = " +nodeId);
        $.getJSON('/plugin_ozwave/' + clientID + '/request/ozwave.node.infos', {
            networkID: NetworkID,
            nodeId: nodeId
            }, 
            function(data, result, request) {
                console.log("Retour de get node infos :" + JSON.stringify(data));
                if (data.result == 'success') {
                    console.log("updating datatable...");
                    data.content.LastReqRefresh = d.getTime();
                    updateNode(data.content);
                } else {
                    console.warn("Request node infos fail (NetworkID = " + NetworkID + ", nodeId = " +nodeId + ") ", data);
                };
            }
        );
    } else {
        console.warn("Can't request undefined address (NetworkID = " + NetworkID + ",nodeId = " +nodeId + ")");
    };
};

function HighlightCell(oCell, timeUpDate) {
    if (timeUpDate) {
        var t = 'Update at ' + Date(timeUpDate);
        oCell.title = t;
   //     createToolTip("#" + oCell.id, 'right', t);
    };
    if (oCell.tagName == 'TD') {
        var elem = oCell;
    } else {
        var elem = $("#" + oCell.id).parents('td');
    };
    var classes = $(elem).attr('class');
    if (classes) {
        if (classes.indexOf("alert-success") != -1) {return;};
        $(elem).removeClass(classes)
    };
    $(elem).addClass('alert-success');
    setTimeout( function(){
        if (classes) {
            $(elem).addClass(classes)
            };
        $(elem).removeClass('alert-success');
        },4000 );
};

function renderBadgeCount(id, count) {
    if (count > 0) {
        $("#"+id).removeClass("hidden");
    } else {
        $("#"+id).removeClass("hidden").addClass("hidden");
    };
    $("#"+id).text(count);
};

function renderInputText(refId, name, dtype, value, title, label) {
    var idInput = name;
    if (typeof refId === 'object') {
        for (n in refId) {idInput += "_" + refId[n];};
    } else {idInput += "_" + refId;};
    var inputRender =  '<form method="POST" action="" class="form-inline">' +
                    '<div class="form-group">' +
                        '<div class="input-group">'
    if (label != undefined) {
        inputRender += '<label class="control-label vert-align" for="'+idInput+'">'+label+'</label>';
    }
    inputRender += '<input type="text" id="'+ idInput +'" class="form-control input-sm" name="'+name+'" datatype="'+dtype+'" title="'+title+'" value="'+value+'">'+
                            '<span class="input-group-addon input-addon-xs"><span id="st_'+ idInput +'" class="btn btn-xs btn-info">' +
                                '<span id="stic_'+ idInput +'" class="glyphicon glyphicon-floppy-saved"></span></span></span>' +
                        '</div>' +
                '</div>' +
            '</form>';
   return inputRender;
};

function EnableInputText(obj, callback) {
    $(obj).attr("isHandled", true);
    $('#st_'+obj.id).attr('disabled', true);
    $(obj).on('keypress keyup', function (e) {
        var ret = true
        if (e.type == 'keypress') {
            if (e.which == 13) {
                callback(e)
                ret = false
            };
        } else {
            if (e.which == 13) {return false};
        };
        if ($('#st_'+this.id).length){
            updateBtStatus(this.id, 'btn-warning');
            if ($('#st_'+this.id).attr("isHandled") != "true") {
                $('#st_'+this.id).attr("isHandled", true);
                $('#st_'+this.id).on('click', callback);
            };
            $('#st_'+this.id).attr('disabled', false);
        };
        return ret;
    });
};

function EnableInputList(obj, callback) {
    $(obj).attr("isHandled", true);
    $(obj).on('changed', function (e) {
        var ret = callback(obj);
    });
};

function EnableButtonAction(obj, callback) {
    $(obj).attr("isHandled", true);
    $('#st_'+obj.id).attr('disabled', true);
    $(obj).on('click', function (e) {
        return callback(obj);
    });
};

function updateBtStatus(refId, newClassSt) {
    var removedClassSt ="";
    var removedClassStic ="";
    var newClassStic = "";
    switch (newClassSt) {
        case 'btn-success':
            removedClassSt = 'btn-warning btn-danger btn-info';
            removedClassStic = 'glyphicon-floppy-save glyphicon-floppy-saved glyphicon-warning-sign';
            newClassStic = 'glyphicon-ok';
            break;
        case 'btn-info':
            removedClassSt = 'btn-warning btn-danger btn-success';
            removedClassStic = 'glyphicon-floppy-save glyphicon-ok glyphicon-warning-sign';
            newClassStic = 'glyphicon-floppy-saved';
            break;
        case 'btn-warning':
            removedClassSt = 'btn-success btn-danger btn-info';
            removedClassStic = 'glyphicon-ok glyphicon-floppy-saved glyphicon-warning-sign';
            newClassStic = 'glyphicon-floppy-save';
            disableBt = false;
            break;
        case 'btn-danger':
            removedClassSt = 'btn-warning btn-success btn-info';
            removedClassStic = 'glyphicon-floppy-save glyphicon-floppy-saved glyphicon-ok';
            newClassStic = 'glyphicon-warning-sign';
            break;
    };
    $('#st_'+refId).removeClass(removedClassSt).addClass(newClassSt);
    $('#stic_'+refId).removeClass(removedClassStic).addClass(newClassStic);
};

function updateBtSavedConf(NetworkID, saved) {
    if (saved) {
        $("#saveconf_" + NetworkID).removeClass("btn-warning hide").addClass("btn-info");
        $("#icsaveconf_" + NetworkID).removeClass("glyphicon-floppy-save glyphicon-hourglass").addClass("glyphicon-floppy-saved");
    } else {
        $("#saveconf_" + NetworkID).removeClass("btn-info hide").addClass("btn-warning");
        $("#icsaveconf_" + NetworkID).removeClass("glyphicon-floppy-saved glyphicon-hourglass").addClass("glyphicon-floppy-save");
    };
};

function updateBtMonitored(nodeData) {
    var nodeRef = GetNodeRefId(nodeData.NetworkID, nodeData.NodeID);
    if (nodeData.Monitored != '') {
        $("#monitornode" + nodeRef).attr('title', "Node monitoring file : " + nodeData.Monitored + "&#10;Click to stop monitoring.");
        $("#monitornodeic" + nodeRef).removeClass("icon16-action-play").addClass("icon16-action-processing_ffffff");
    } else {
        $("#monitornode" + nodeRef).attr('title', "Start Monitor Node and log it.");
        $("#monitornodeic" + nodeRef).removeClass("icon16-action-processing_ffffff").addClass("icon16-action-play");
    };
};

function setValueCmdClss(refId, newValue) {
    var idValuesNode = '#valuesNode' + GetNodeRefId(refId[1], refId[2]);
    var table = $(idValuesNode).DataTable();
    sendRequest("ozwave.value.set", {"newValue": newValue, "networkId":  refId[1], "nodeId":  refId[2], "valueId": refId[3]}, function(data, result) {
        if (result == "error" || data.result == "error") {
                new PNotify({
                    type: 'error',
                    title: 'Set a value CommandClass',
                    text: data.content.error,
                    delay: 6000
                });
            } else {
                var valueData = GetValueZWNode(data.content.NetworkID, data.content.NodeID, data.content.ValueID);
                valueData.value = data.content.value;
                RefreshValueNodeData(data.content.NetworkID, data.content.NodeID, valueData);
                var cell = GetValueCell(table, GetValueRefId(data.content.NetworkID, data.content.NodeID, data.content.ValueID), 3);
                cell.data(data.content.value).draw('page');
                HighlightCell(cell.node());
                new PNotify({
                    type: 'success',
                    title: 'Set a value CommandClass',
                    text: 'Node ' + valueData.nodeId + ', instance ' + valueData.instance +', ' + valueData.label +  ' is set to "' + data.content.value + '"',
                    delay: 4000
                });
            };
    });
};   

// DataTable Nodes renderers
function renderNodeStatusCol(data, type, full, meta) {
     /* {0:,
              1:'Initialized - not known', 
              2:'Completed',
              3:'In progress - Devices initializing',
              4:'In progress - Linked to controller',
              5:'In progress - Can receive messages', 
              6:'Out of operation'} */
    var api = $.fn.dataTable.Api(meta.settings);
    var cell = api.cell(meta.row, 0);
    var refId = cell.data().split(".");
    var nodeRef = GetNodeRefId(refId[0], refId[1]);
    var nodeData = GetZWNode(refId[0], refId[1]);    
    var status = 'status-unknown';
    try {
        var initState = nodeData.InitState.toLowerCase();
        }
    catch (err) {
        // console.log(err);
        var initState ='uninitialized';
        };
    if (initState =='uninitialized') {status = 'status-unknown';};
    if (initState =='initialized - not known') {status = 'status-active';};
    if (initState =='completed') {status ='status-active';};
    if (initState.indexOf('in progress') !=-1) {status ='action-processing_ffffff';};
    if (initState =='out of operation') {status ='status-warning';};
    var str = '' + nodeData.NodeID;
    while (str.length < 3) {str = '0' + str;};
    var bat = '';
    if (nodeData.BatteryLevel != -1) {
        var st = '0'
            if (nodeData.BatteryLevel >= 85) {st = '100';
            } else if (nodeData.BatteryLevel >= 60) {st = '80';
            } else if (nodeData.BatteryLevel >= 40) {st = '50';
            } else if (nodeData.BatteryLevel >= 25) {st = '30';
            } else if (nodeData.BatteryLevel >= 15) {st = '20';
            } else if (nodeData.BatteryLevel >= 5) {st = '10';};
        bat = "<span id='battery" + nodeData.NodeID + "' class='glyphicon btnspacing icon16-status-battery-" + st +"' title='Battery level " + nodeData.BatteryLevel + " %'></span>";
        var bCheck = "";
        var tCheck =  "Check to request battery level at each awake.";
        if (nodeData.BatteryChecked) { 
            bCheck = " checked";
            tCheck = "Battery level is requested at each awake.";
        };
        bat += "<input type='checkbox' class='medium' id='batcheck" + nodeRef + "' " + bCheck + " title='"+ tCheck + "'/>"
    };
    return  str + "<span id='nodestate" + nodeData.NodeID + "' class='glyphicon btnspacing icon16-" + status + 
               "' title='" + nodeData.InitState + "\n Current stage : " + nodeData.Stage + "'></span>" + bat;
};

function renderNodeNameCol(data, type, full, meta) {
    var api = $.fn.dataTable.Api(meta.settings);
    var cell = api.cell(meta.row, 0);
    var nodeData = GetZWNodeByRow(cell);
    if (nodeData) {
        return renderInputText(cell.data().split("."), "name", "node", nodeData.Name, "Node name");
    } else {
        return 'No Data';
    };
};

function renderNodeLocationCol(data, type, full, meta) {
    var api = $.fn.dataTable.Api(meta.settings);
    var cell = api.cell(meta.row, 0);
    var nodeData = GetZWNodeByRow(cell);
    if (nodeData) {
        return renderInputText(cell.data().split("."), "location", "node", nodeData.Location, "Node location");
    } else {
        return 'No Data';
    };
};

function renderNodeAwakeCol(data, type, full, meta) {
    var api = $.fn.dataTable.Api(meta.settings);
    var cell = api.cell(meta.row, 0);
    var nodeData = GetZWNodeByRow(cell);
    if (nodeData) {
        if (nodeData['lastStatus'] === undefined) {dt= '';
        } else {dt = ' since : ' + nodeData['lastStatus'];};
        if (nodeData['State sleeping']==true) { //Sleeping
            textstatus = 'Inactive on network' + dt;
            st = 'icon-warning glyphicon-bed' //'unknown';
        } else { //actif
            textstatus = 'Active on network' + dt;
            st = 'icon-success glyphicon-signal';
        };
        return  "<span id='infosleepnode" + nodeData.NodeID + "'class='glyphicon " + st + "' title='" + textstatus + "' /span>";
    } else {
        return 'No Data';
    };
};

function renderNodeTypeCol(data, type, full, meta) {
    var api = $.fn.dataTable.Api(meta.settings);
    var cell = api.cell(meta.row, 0);
    var nodeData = GetZWNodeByRow(cell);
    if (nodeData) {
        var text = '';
        if (nodeData.Capabilities.length > 1) {text= 'Capabilities :\n';
        } else {text= 'Capability :\n';};
        for (i=0; i<nodeData.Capabilities.length; i++) {
            text = text + " -- " + nodeData.Capabilities[i] + '\n';
        }
        return  nodeData.Type + "  <span id='infotypenode" + nodeData.NodeID +"' class='icon-info glyphicon glyphicon-info-sign' title='" + text + "' /span>";
    } else {
        return 'No Data';
    };
};
    
function renderNodeActionColl(data, type, full, meta) {
    var api = $.fn.dataTable.Api(meta.settings);
    var cell = api.cell(meta.row, 0);
    var refId = cell.data().split(".");
    var nodeRef = GetNodeRefId(refId[0], refId[1]);
    var nodeData = GetZWNode(refId[0], refId[1]);
    if (nodeData) {
        var stAct = 'fa-search-plus';
        var tabDet = document.getElementById("valuesNode" + nodeRef);
        if (tabDet) { // DetailNode opened 
            stAct = 'fa-search-minus'; 
        };
        var ret = "<span id='detailnode" + nodeRef + "' type='nodeaction' class='btn btn-xs btnspacing btn-info' title='CommandClass detail'>" +
                        "<span id='detailnodeic" + nodeRef + "' class='fa " + stAct + "'></span></span>"
        ret += "<span id='refreshnode" + nodeRef + "' type='nodeaction' class='btn btn-xs btnspacing btn-info' title='Force Refresh Node'>" +
                        "<span id='refreshnodeic" + nodeRef + "' class='glyphicon glyphicon-refresh'></span></span>"
        if (nodeData.Groups.length > 0) {
            ret += "<span id='updassoc" + nodeRef + "' type='nodeaction' class='btn btn-xs extbtn btn-info' title='Edit association'>" +
                        "<span id='updassocic" + nodeRef + "' class='glyphicon icon16-action-groups'></span></span>"
            };
        var stMonitored = "action-play";
        var tMonitored = "Start Monitor Node and log it.";
        if (nodeData.Monitored != '') {
            stMonitored = "action-processing_ffffff";
            tMonitored = "Node monitoring file : " + nodeData.Monitored + "/n/nClick to stop monitoring.";
            };

        ret += "<span id='monitornode" + nodeRef + "' type='nodeaction' class='btn btn-xs extbtn btn-info' title='" +tMonitored + "'>" +
                "<span id='monitornodeic" + nodeRef + "' class='glyphicon icon16-" + stMonitored + "'></span></span>"
        return  ret;
    } else {
        return 'No Data';
    };
};

function GetNodeCell(table, nodeId, col) {
    try {
        var row = $("#node-"+ nodeId);
        var index = table.cell(row).index();
        var cell = table.cell(index.row, col);
        }
    catch (err) {
        var cell = false;
        };
    return cell
};

function addNodeTableRow(table, nodeData) {
     if (table) {
        row = table.row.add([
            nodeData.NetworkID + "." + nodeData.NodeID,
            nodeData.Name,
            nodeData.Location,
            nodeData.Model,
            nodeData["State sleeping"],
            nodeData.Type,
            nodeData["Last update"],
            "Actions..."
        ]);
        var rowNode = row.node()
        var cell = table.cell(rowNode, 0).node();
        $(cell).attr("id", "node-"+ nodeData.NodeID);
        row.draw();
        // highligth cell
        var classes = $(cell).attr('class');
        if (classes) {
            $(cell).removeClass(classes)
        };
        $(cell).addClass('alert-info');
        setTimeout( function(){
            $(cell).removeClass('alert-info');
            if (classes) {
                $(cell).addClass(classes)
                };
            },4000 );
    };
};

function updateNodeTableCell(cell, colName, nodeData, date) {
    // return true after updating
    if (date === undefined) {
        var d = new Date();
        date = d.toLocaleString();
    };
    switch (colName) {
        case "Node":
        case "InitState":
        case "BatteryLevel":
            cell.data(nodeData.NetworkID +"."+ nodeData.NodeID).draw('page');
            break;
        case "Name":
            cell.data(nodeData.Name).draw('page');
            break;
        case  "Location":
            cell.data(nodeData.Location).draw('page');
            break;
        case "Model":
            cell.data(nodeData.Model).draw('page');
            break;
        case "State Sleeping":
            cell.data(nodeData['State Sleeping']).draw('page');
            break;
        case "Type":
        case "Capabilities":
            cell.data(nodeData['Type']).draw('page');
            break;
        case "Last update":
            cell.data(nodeData['Last update']).draw('page');
            break;
        default:
            return false;
    };
    HighlightCell(cell.node(), date);
    return true;
};
