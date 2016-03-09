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


// Handle all messages for nodes state, init, change, value updating.
function HandleDataNodeUpdMsg(data) {
    var nodeData = GetZWNode(data.content.NetworkID, data.content.NodeID);
    if (nodeData) {
        switch (data.content.type){
            case 'node-state-changed':
                var refresh = false;
                var dTableCol = [];
                switch (data.content.data.state) {
                    case "sleep" :
                        nodeData['State sleeping'] = data.content.data.value;
                        nodeData.lastStatus = data.content.data.lastStatus;
                        dTableCol.push({col: 4, value: data.content.data.value});
                        refresh = true;
                        break;
                    case "Named" :
                        if (nodeData.Name != data.content.data.name && data.content.data.name != "") {
                            nodeData.Name = data.content.data.name;
                            dTableCol.push({col: 1, value: data.content.data.name});
                        };
                        if (nodeData.Location != data.content.data.location && data.content.data.location != "") {
                            nodeData.Location = data.content.data.location;
                            dTableCol.push({col: 2, value: data.content.data.location});
                        };
                        if (nodeData.Model != data.content.data.model && data.content.data.model != " -- ") {
                            nodeData.Model = data.content.data.model;
                            dTableCol.push({col: 3, value: data.content.data.model});
                        };
                        refresh = true;
                        break;
                    case "DmgDevices" :
                        if (data.content.data.DmgDevices != undefined) {nodeData['DmgDevices'] = data.content.data.DmgDevices;};
                        if (data.content.data.KnownDeviceTypes != undefined) {nodeData['KnownDeviceTypes'] = data.content.data.KnownDeviceTypes;};
                        if (data.content.data.NewDeviceTypes != undefined) {nodeData['NewDeviceTypes'] = data.content.data.NewDeviceTypes;};
                        dTableCol.push({col: 0, value: data.content.NetworkID+"."+data.content.NodeID});
                        refresh = true;
                        break;
                    case "GrpsAssociation" :
                        nodeData['Groups'] = data.content.data.Groups;
                        dTableCol.push({col: 7, value: data.content.NetworkID+"."+data.content.NodeID});
                        refresh = true;
                        break;
                    case "Neighbors" :
                        nodeData['Neighbors'] = data.content.data.Neighbors;
                        refresh = true;
                        break;
                };
                if (refresh) {
                    RefreshDataNode(nodeData);
                    try { var table = $("#tabnodes_" + data.content.NetworkID).DataTable();
                    } catch (err) { var table = false; };
                    if (table) {   // DataTable exit so update it.
                        var d = new Date();
                        var date = d.toLocaleString();
                        for (i=0; i < dTableCol.length; i++) {
                            var cell = GetNodeCell(table, data.content.NodeID, dTableCol[i].col);
                            if (cell) {
                                cell.data(dTableCol[i].value).draw('page');
                                HighlightCell(cell.node(), date);
                            } else { // Adding node in dataTable.
                                requestZWNodeInfos(data.content.NetworkID, data.content.NodeID);
                                break;
                            };
                        };
                    };
                };
                break;
            case 'init-process' :
                nodeData.InitState = data.content.data;
                RefreshDataNode(nodeData);
                try { var table = $("#tabnodes_" + data.content.NetworkID).DataTable();
                } catch (err) { var table = false; };
                if (table) {   // DataTable exit so update it.
                    var cell = GetNodeCell(table, data.content.NodeID, 0);
                    if (cell) {
                        var nodeData = GetZWNode(data.content.NetworkID, data.content.NodeID);
                        cell.data(data.content.NetworkID+"."+data.content.NodeID).draw('page');  // set data required to force draw
                        var d = new Date();
                        var date = d.toLocaleString();
                        HighlightCell(cell.node(), date);
                    };
                };
                requestZWNodeInfos(data.content.NetworkID, data.content.NodeID);
                break;
            case 'node-removed' :
                RemoveDataNode(nodeData);
                try { var table = $("#tabnodes_" + data.content.NetworkID).DataTable();
                } catch (err) { var table = false; };
                if (table) {   // DataTable exit so update it.
                    var cell = GetNodeCell(table, data.content.NodeID, 0);
                    if (cell) {
                        var row = table.row(cell.index().row);
                        row.remove().draw;
                    };
                };
                new PNotify({
                            type: 'success',
                            title: 'Exclusion.',
                            text: data.content.usermsg,
                            delay: 4000
                    });
                break;
            case 'value-changed' :
                if (nodeData.Values != undefined) {
                    for (var v in nodeData.Values) {
                        if (nodeData.Values[v].id == data.content.data.id) {
                            nodeData.Values[v].value = data.content.data.value;
                            nodeData.Values[v].realvalue = data.content.data.realvalue;
                            RefreshValuesNodeData(nodeData.Values);
                            var table = $('#valuesNode' + GetNodeRefId(data.content.NetworkID, data.content.NodeID)).DataTable();
                            var cell = GetValueCell(table, GetValueRefId(data.content.NetworkID, data.content.NodeID, data.content.data.id), 3);
                            if (cell) {
                                cell.data(data.content.data.value).draw('page');  // set data required to force draw
                                var d = new Date();
                                var date = d.toLocaleString();
                                HighlightCell(cell.node(), date);
                            };
                            break;
                        };
                    };
                };
                break;
        };
    } else { // Node not known in JS so requesing all node data to add it
        requestZWNodeInfos(data.content.NetworkID, data.content.NodeID);
    };
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
        } else {
            if (neighborsGraph) { neighborsGraph.addNode(nodesData[idx]); };
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

function RemoveDataNode(dataNode) {
    var idx = -1;
    for (var i = 0; i < nodesData.length; i++) {
        if (nodesData[i].NodeID == dataNode.NodeID) {
            idx = i;
            break;
        };
    };
    if (idx != -1) {
        if (nodesData[idx].ktcNode) {
            nodesData[idx].ktcNode.destroy();
        };
        nodesData.splice(idx, 1);
    };
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
            if (groups) {
                if (groups[0].idx != undefined) {
                    nodesData[i].Groups = groups;
                } else {
                    var exist = false;
                    for (var g=0; g <groups.length; g++) {
                        exist = false;
                        for (var grp=0; grp<nodesData[i].Groups.length; grp++) {
                            if (nodesData[i].Groups[grp].idx == groups[g].idx) {
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
    try { var table = $("#tabnodes_" + newNodeData.NetworkID).DataTable();
    } catch (err) { var table = false; };
    var keyToUpdate = [];
    if (nodeData) { // Node allready exist in nodesData list
        for (key in newNodeData) { // update or add key
            if (nodeData[key] != newNodeData[key]) {
                nodeData[key] = newNodeData[key];
                keyToUpdate.push(key);
            };
        };
        nodeData = RefreshDataNode(nodeData);
        if (table) {
            var nodeTableColUpd = {};
            for (key in keyToUpdate) {
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

function renderNodeName(nodeData) {
    if (nodesData[n].Name == "Undefined") {
        return nodesData[n].NodeID + ' : ' + nodesData[n].Model;
    } else {
        return nodesData[n].NodeID + ' : ' + nodesData[n].Name + ' - ' + nodesData[n].Model;
    };
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
    inputRender += '<input type="text" id="'+ idInput +'" class="form-control input-sm" name="'+name+'" datatype="'+dtype+
                            '" data-toggle="tooltip" data-placement="bottom" title="'+title+'" value="'+value+'">'+
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
        $("#monitornodeic" + nodeRef).removeClass("fa-play").addClass("fa-refresh fa-spin icon-danger");
    } else {
        $("#monitornode" + nodeRef).attr('title', "Start Monitor Node and log it.");
        $("#monitornodeic" + nodeRef).removeClass("fa-refresh fa-spin icon-danger").addClass("fa-play");
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
    var initStateExt = '';
    if (initState =='uninitialized') {status = 'fa-question-circle icon-unknown';};
    if (initState =='initialized - not known') {status = 'fa-circle icon-info';};
    if (initState =='completed') {status ='fa-circle icon-success';};
    if (initState.indexOf('in progress') !=-1) {status ='fa-spinner fa-spin icon-info';};
    if (initState =='in progress - devices initializing') {
        status ='fa-gear fa-spin icon-success';
        initStateExt = ' (Wait to retrieve config parameters)';
    };
    if (initState =='out of operation') {status ='fa-warning icon-danger';};
    var str = '' + nodeData.NodeID;
    while (str.length < 3) {str = '0' + str;};
    var bat = '';
    if (nodeData.BatteryLevel != -1) {
        var st = 'fa-battery-empty icon-unknown'
            if (nodeData.BatteryLevel >= 85) {st = 'fa-battery-full icon-success';
            } else if (nodeData.BatteryLevel >= 70) {st = 'fa-battery-three-quarters icon-success';
            } else if (nodeData.BatteryLevel >= 40) {st = 'fa-battery-half icon-success';
            } else if (nodeData.BatteryLevel >= 25) {st = 'fa-battery-quarter icon-success';
            } else if (nodeData.BatteryLevel >= 15) {st = 'fa-battery-quarter icon-warning';
            } else if (nodeData.BatteryLevel >= 5)  {st = 'fa-battery-empty icon-danger';};
        bat = "<span id='battery" + nodeData.NodeID + "' class='fa btnspacing fa-rotate-270 " + st +
                "' data-toggle='tooltip' data-placement='right' title='Battery level<br>" + nodeData.BatteryLevel + " %'></span>";
        var bCheck = "";
        var tCheck =  "Check to request battery level at each awake.";
        if (nodeData.BatteryChecked) {
            bCheck = " checked";
            tCheck = "Battery level is requested at each awake.";
        };
        bat += "<input type='checkbox' class='medium' id='batcheck" + nodeRef + "' " + bCheck +
                   " data-toggle='tooltip' data-placement='right' title='"+ tCheck + "'/>"
    };
    var devState = "";
    var devContent = "";
    var dmgDev = "";
    var knDev = "";
    var newDev = "";
    if (nodeData.DmgDevices.length != 0) {
        devState = "fa-check-circle icon-success";
        devContent = '<div class="container-fluid">';
        for (nD in nodeData.DmgDevices) {
            var header = nodeData.DmgDevices[nD].name
            if (nodeData.DmgDevices[nD].parameters.instance != undefined) {
                header += ", instance " + nodeData.DmgDevices[nD].parameters.instance.value;
            };
            devContent += "<p><strong>"+ header + " :</strong><pre>"  + JSON.stringify(nodeData.DmgDevices[nD], null, 2) + "</pre></p>";
        };
        devContent += "</div>";
        dmgDev = "<span id='nodedmgdevices"+ nodeData.NodeID + "' class='fa fa-check-circle icon-success extbtn'" +
                " data-toggle='popover' title='Domogik device associated'" +
                " data-container='body' data-content='" + devContent + "'></span>";
    };
    if (Object.keys(nodeData.KnownDeviceTypes).length != 0) {
        devContent = '<div class="container-fluid">';
        var find = false;
        for (nD in nodeData.KnownDeviceTypes) {
            var insert = true;
            if (dmgDev != ""){
                dRef = nD.split(".");
                var compRS = dRef[1]; // Node ID compare
                var compRD = "node";
                if (dRef.length == 3) {
                    compRS = dRef[2]; // Instance compare
                    compRD = "instance";
                };
                for (nDT in nodeData.DmgDevices) {
                    if ((nodeData.DmgDevices[nDT].parameters[compRD] != undefined &&
                         nodeData.DmgDevices[nDT].device_type_id == nodeData.KnownDeviceTypes[nD] &&
                         compRS == nodeData.DmgDevices[nDT].parameters[compRD].value)) {
                    insert = false;
                    break;
                    };
                };
            };
            if (insert) {
                devContent += "<p><strong>"+ nD + " :</strong> " + JSON.stringify(nodeData.KnownDeviceTypes[nD], null, 2) + "</p>";
                find = true;
            };
        };
        devContent += "</div>";
        if (find) {
            knDev = "<span id='knowndevicetypes"+ nodeData.NodeID + "' class='fa fa-asterisk icon-warning extbtn'" +
                    " data-toggle='popover' title='<h4>No domogik device associate.<br>Create it with device-type :</h4>'" +
                    " data-container='body' data-content='" + devContent + "'></span>";
        };
    };
    if (Object.keys(nodeData.NewDeviceTypes).length != 0) {
        devContent = '<div class="container-fluid">';
        for (nD in nodeData.NewDeviceTypes) {
            devContent += "<p><strong>"+ nD + " :</strong><pre>" + JSON.stringify(nodeData.NewDeviceTypes[nD], null, 2) + "</pre></p>";
        };
        devContent += "</div>";
        newDev = "<span id='newdevicetypes"+ nodeData.NodeID + "' class='fa fa-plus-square icon-warning extbtn'" +
                " data-toggle='popover' title='<h4>No domogik device type associate.<br>Send a developper request to create it with :</h4>'" +
                " data-container='body' data-content='" + devContent + "'></span>";
    };
    if (devContent == "") {
        devContent = "";
        if (initState !='completed') {devContent = "Wait for complet initialisation...";
        } else {devContent = "Try to launch detection again...";};
        dmgDev = "<span id='nodedmgdevices"+ nodeData.NodeID + "' class='fa fa-exclamation-circle icon-danger extbtn'" +
               " data-toggle='popover' title='Neither domogik device type find !'" +
               " data-content='" + devContent + "'></span>";
    }
    return  str + "<span id='nodestate" + nodeData.NodeID + "' class='fa extbtn " + status +
                "' data-toggle='tooltip' data-placement='right' title='" +
                nodeData.InitState + initStateExt + "<br> Current stage : " + nodeData.Stage + "'></span>" + bat +
                dmgDev + knDev + newDev;
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
        } else {dt = ' since :<br>' + nodeData['lastStatus'];};
        if (nodeData['State sleeping']==true) { //Sleeping
            textstatus = 'Inactive on network' + dt;
            st = 'icon-warning glyphicon-bed' //'unknown';
        } else { //actif
            textstatus = 'Active on network' + dt;
            st = 'icon-success glyphicon-signal';
        };
        return  "<span id='infosleepnode" + nodeData.NodeID + "'class='glyphicon " + st + "'" +
                " data-toggle='tooltip' data-placement='left' title='" + textstatus + "' /span>";
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
        if (nodeData.Capabilities.length > 1) {text= 'Capabilities :<br>';
        } else {text= 'Capability :<br>';};
        for (i=0; i<nodeData.Capabilities.length; i++) {
            text = text + " -- " + nodeData.Capabilities[i] + '<br>';
        }
        return  nodeData.Type + " <span id='infotypenode" + nodeData.NodeID +"' class='fa fa-info-circle fa-lg icon-info'"+
                " data-toggle='tooltip' data-placement='bottom' title='" + text + "' /span>";
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
        var ret = "<span id='detailnode" + nodeRef + "' type='nodeaction' class='btn btn-xs btnspacing btn-info'" +
                        " data-toggle='tooltip' data-placement='left' title='CommandClass detail'>" +
                        "<span id='detailnodeic" + nodeRef + "' class='fa " + stAct + "'></span></span>"
        ret += "<span id='refreshnode" + nodeRef + "' type='nodeaction' class='btn btn-xs btnspacing btn-info'" +
                        " data-toggle='tooltip' data-placement='left' title='Force Refresh Node'>" +
                        "<span id='refreshnodeic" + nodeRef + "' class='glyphicon glyphicon-refresh'></span></span>"
        if (nodeData.Groups.length > 0) {
            ret += "<span id='updassoc" + nodeRef + "' type='nodeaction' class='btn btn-xs btnspacing btn-info'" +
                        " data-toggle='tooltip' data-placement='left' title='Edit association'>" +
                        "<span id='updassocic" + nodeRef + "' class='fa fa-link'></span></span>"
            };
        var stMonitored = "fa-play";
        var tMonitored = "Start Monitor Node and log it.";
        if (nodeData.Monitored != '') {
            stMonitored = "fa-refresh fa-spin icon-danger";
            tMonitored = "Node monitoring file : " + nodeData.Monitored + "/n/nClick to stop monitoring.";
            };

        ret += "<span id='monitornode" + nodeRef + "' type='nodeaction' class='btn btn-xs btnspacing btn-info'" +
                " data-toggle='tooltip' data-placement='left' title='" +tMonitored + "'>" +
                "<span id='monitornodeic" + nodeRef + "' class='fa " + stMonitored + "'></span></span>"
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
