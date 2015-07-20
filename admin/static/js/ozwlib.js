var clientID ="";
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
    

// Handle Data nodes table

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

function GetZWNode(NetworkID, nodeiId) {
    for (var i=0; i< nodesData.length; i++) {
        if ((nodesData[i].NodeID == nodeiId) && (nodesData[i].NetworkID == NetworkID)) {
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
        $.getJSON('/plugin_ozwave/' + clientID + '/'+ NetworkID + '/' + nodeId + '/infos', {}, 
            function(data, result) {
                console.log("Retour de get node infos :" + JSON.stringify(data));
                if (data.result == 'success') {
                    console.log("updating datatable...");
                    data.data.LastReqRefresh = d.getTime();
                    updateNode(data.data);
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

function  saveUpdate(event) {
    var data = event.data.callback(event.data.obj);
    if (data.result == 'error') {
        new PNotify({
                type: 'error',
                title: 'Invalid input',
                text: data.msg,
                delay: 6000
        });
        if ($('#st_'+event.data.obj.id).length){  
            updateBtStatus(event.dat.obj.id, 'btn-danger');
        };
    } else {
        $(event.data.obj).val(data.value);
        if ($('#st_'+event.data.obj.id).length){  
            updateBtStatus(event.data.obj.id, 'btn-success');
        };
    };
    return false;
};

function EnableInputText(obj, callback) {
    $(obj).attr("isHandled", true);
    $('#st_'+obj.id).attr('disabled', true);
    $(obj).on('keypress keyup', function (e) {
        if (e.type == 'keypress') {
            if (e.which == 13) {
                return saveUpdate({data: {obj: obj, callback:callback}});
            };
        } else {
            if (e.which == 13) {return false};
        };
        if ($('#st_'+this.id).length){
            updateBtStatus(this.id, 'btn-warning');
            $('#st_'+this.id).on('click', {obj: this, callback: callback}, saveUpdate);
            $('#st_'+this.id).attr('disabled', false);
        };
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

// DataTable Nodes renderers
function renderNodeStatusCol(data, type, full, meta) {
     /* {0:,
              1:'Initialized - not known', 
              2:'Completed',
              3:'In progress - Devices initializing',
              4:'In progress - Linked to controller',
              5:'In progress - Can receive messages', 
              6:'Out of operation'} */
        var nodeRef= data.split(".");
        var nodeData = GetZWNode(nodeRef[0], parseInt(nodeRef[1]));
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
        }
    return  str + "<span id='nodestate" + nodeData.NodeID + "' class='glyphicon btnspacing icon16-" + status + "' title='" + nodeData.InitState + "\n Current stage : " + nodeData.Stage + "'></span>" + bat;
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
    var nodeData = GetZWNodeByRow(cell);
    if (nodeData) {
        var stAct = 'glyphicon-zoom-in';
        var tabDet = document.getElementById("detNode" + nodeData.NodeID);
        if (tabDet) { // DetailNode opened 
            stAct = 'glyphicon-zoom-out'; 
        };
        var ret = "<span id='detailnode_" + nodeData.NodeID + "' class='btn btn-xs btnspacing btn-info' title='CommandClass detail'>" +
                        "<span id='detailnodeic_" + nodeData.NodeID + "' class='glyphicon " + stAct + "'></span></span>"
        ret += "<span id='refreshnode_" + nodeData.NodeID + "' class='btn btn-xs btnspacing btn-info' title='Force Refresh Node'>" +
                        "<span id='refreshnodeic_" + nodeData.NodeID + "' class='glyphicon glyphicon-refresh'></span></span>"
        if (nodeData.Groups.length > 0) {
            ret += "<span id='updassoc_" + nodeData.NodeID + "' class='btn btn-xs extbtn btn-info' title='Edit association'>" +
                        "<span id='updassocic_" + nodeData.NodeID + "' class='glyphicon icon16-action-groups'></span></span>"
            };
        var stMonitored = "action-play";
        var tMonitored = "Start Monitor Node and log it.";
        if (nodeData.Monitored != '') {
            stMonitored = "action-processing_ffffff";
            tMonitored = "Node monitoring file : " + nodeData.Monitored + "<BR><BR>Click to stop monitoring.";
            };

        ret += "<span id='monitornode_" + nodeData.NodeID + "' class='btn btn-xs extbtn btn-info' title='" +tMonitored + "'>" +
                "<span id='monitornodeic_" + nodeData.NodeID + "' class='glyphicon icon16-" + stMonitored + "'></span></span>"
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
            cell.data(nodeData.NetworkID +"."+ nodeData.NodeID).draw();
            break;
        case "Name":
            cell.data(nodeData.Name).draw();
            break;
        case  "Location":
            cell.data(nodeData.Location).draw();
            break;
        case "Model":
            cell.data(nodeData.Model).draw();
            break;
        case "State Sleeping":
            cell.data(nodeData['State Sleeping']).draw();
            break;
        case "Type":
        case "Capabilities":
            cell.data(nodeData['Type']).draw();
            break;
        case "Last update":
            cell.data(nodeData['Last update']).draw();
            break;
        default:
            return false;
    };
    HighlightCell(cell.node(), date);
    return true;
};
