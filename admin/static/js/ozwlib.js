
function renderBadgeCount(id, count) {
    if (count > 0) {
        $("#"+id).removeClass("hidden");
    } else {
        $("#"+id).removeClass("hidden").addClass("hidden");
    };
    $("#"+id).text(count);
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
//    var nTable = $("[id^='tabnodes_']").DataTable();
//    var data2 = nTable.cell(meta.row, meta.col}).node()
    try {
        var node = JSON.parse(data);
        var cell = $("#node-"+ node.nodeId);
        var nodeData = JSON.parse($(cell).attr("nodeData"));
        }
    catch (err) {
        console.log(err);
        return 'No Data'
        };
    var status = 'status-unknown';
    var initState = nodeData.InitState.toLowerCase();
    if (initState =='uninitialized') {status = 'status-unknown';};
    if (initState =='initialized - not known') {status = 'status-active';};
    if (initState =='completed') {status ='status-active';};
    if (initState.indexOf('in progress') !=-1) {status ='action-processing_ffffff';};
    if (initState =='out of operation') {status ='status-warning';};
    var str = '' + node.nodeId;
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
        bat = "<span id='battery" + node.nodeId + "'class='icon16-text-right  icon16-status-battery-" + st +"' title='Battery level " + nodeData.BatteryLevel + " %'></span>";
        }
    return  str + "<span id='nodestate" + node.nodeId + "'class='icon16-text-right  icon16-" + status + "' title='" + nodeData.InitState + "'></span>" + bat;
};

