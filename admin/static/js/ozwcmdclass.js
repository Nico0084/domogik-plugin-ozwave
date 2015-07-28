function initValuesTab(refId) {
 return '<div class="contenaire-fluid">'+
             '<table id="valuesNode'+refId+'" class="display cell-border" cellspacing="0" width="100%">'+
                '<thead>'+
                    '<tr>'+
                        '<th>Status</th>'+
                        '<th>Index</th>'+
                        '<th>Type</th>'+
                        '<th>Value</th>'+
                        '<th>Units</th>'+
                        '<th>Command Class</th>'+
                        '<th>Instance</th>'+
                        '<th>Label</th>'+
                        '<th>Genre</th>'+
                    '</tr>'+
                '</thead>'+
                '<tbody>'+
                '</tbody>'+
             '</table>'+
           '</div>'
    };

function buildValuesTab (data) {
    if (data.Values.length != 0) {
        var thOut = Object.keys(data.Values[0]);  // Hypothèse, vrais pour l'intant, toutes les lignes on les mêmes entêtes !
        thOut.unshift('Num', 'realValue');
        var RowN = [];
        var hdCmdClss = {};
        for (i=0; i<thOut.length; i++) {
            hdCmdClss[thOut[i]]= i;
            };
        $.each(data.Values, function (i, value) {
            var R = [];
            R[0] = data.NetworkID+'.'+data.NodeID+'.'+value.id;
            R[1] = value.index;
            R[2] = value.type;
            R[3] = value.value;
            R[4] = value.units;
            R[5] = value.commandClass;
            R[6] = value.instance;
            R[7] = value.label;
            R[8] = value.genre;
            RowN[i] = R;
        });
//            console.log("Dans createValuesTab : " + RowN);
        var idValuesNode = '#valuesNode' + GetNodeRefId(data['NetworkID'], data['NodeID']);
        $(idValuesNode).dataTable({
            "paging":   true,
            "ordering": true,
            "order": [[ 0, "asc" ]],
            "lengthMenu": [[10, 20, 35, -1], [10, 20, 35, "All"]],
            "info": true,
            "columnDefs": [{
                "targets": 0,
                "render": function (data, type, full, meta) {return renderCmdClssStatus(data, type, full, meta);}
                },{
                "targets": 3,
                "width": "20%",
                "render": function (data, type, full, meta) {return renderCmdClssValue(data, type, full, meta);}
                },{
                "targets": 5,
                "render": function (data, type, full, meta) {return renderCmdClssName(data, type, full, meta);}
                }
            ],
//                "fnDrawCallback": function(oSettings) {
//                    handleChangeVCC();
//                    var iId = getDataTableColIndex(oSettings, 'id');
//                    var nodeid = getDataTableColIndex(oSettings, 'nodeId');
//                    var start = oSettings._iDisplayStart;
//                    var stop =  oSettings._iDisplayEnd;
//                    var iIntensity = getDataTableColIndex(oSettings, 'pollintensity');
//                    vTable = this;
//                    for (i=start; i<stop; i++) {
//                        var vData = this.fnGetData(i)
//                        var vId = vData[iId]
//                        var intensity = vData[iIntensity]
//                        createToolTip('#st' + vId, 'bottom');
//                        createToolTip('#hn' + vId, 'bottom');
//                        createToolTip('#adr' + vId, 'bottom');
//                        createToolTip('#hc' + vId, 'top');
//                        createToolTip('#poll' + vId, 'top');
//                        if ($('#poll' + vId).attr('isHandled') === undefined) {
//                            $('#set_polling_value').dialog_form('updbutton', {
//                                title: "{% trans 'Set polling value index ' %}" + (i +1) +"{% trans ', node ' %}" + vData[nodeid],
//                                button: "#poll" + vId,
//                                values: {polled: $('#poll' + vId).is(':checked'), intensity : intensity, valueid: vId},
//                                onok: function(values) {
//                                    // Submit form
//                                    console.log("set checkbox value : " + values.polled + ", intensity :  " + values.intensity);
//                                    setPollingValue(vTable, vData[nodeid], values.valueid, values.polled == 'True', values.intensity);
//                                    $('#set_polling_value').dialog('close');
//                                }
//                            });
//                            $('#poll' + vId).click(function(e){
//                                var vId =  this.id.slice(4)
//                                var obj = $('#hc' + vId);
//                                var cInt = getDataTableColIndex(oSettings, 'pollintensity');
//                                var vPos = vTable.fnGetPosition(obj[0].parentNode);
//                                var vData = vTable.fnGetData(vPos[0]);
//                                var intensity = vData[cInt];
//                                if (intensity == 0) {intensity =1;};
//                                $('#valueid').hide();
//                                $('#tipsSetPollt').html("<br>" + getValueTabCmdClass(vTable, vData, 'commandClass') + " -> " + getValueTabCmdClass(vTable, vData, 'label'));
//                                $('#intensity').val(intensity);
//                                if ($('#poll' + vId).is(':checked')) {
//                                    $('#poll' + vId).removeAttr('checked');
//                                    $('#polled').removeAttr('checked');
//                                } else {
//                                    $('#poll' + vId).attr('checked', 'checked');
//                                    $('#polled').attr('checked', 'checked');
//                                };
//                                console.log("click checkbox value : " + this.id + "  " + vId);
//                                }); 
//                            $('#poll' + vId).attr('isHandled',true)
//                            };
//                        };
//                    var hideCols= ['realValue', 'nodeId', 'homeId','domogikdevice','help' ,'readOnly', 'listElems', 'id','polled','pollintensity']
//                    for (i=0; i<thOut.length; i++) {
//                        if (hideCols.indexOf(thOut[i]) != -1) {
//                            $(idValuesNode).dataTable().fnSetColumnVis( i, false ); };
//                        }
//                },
                "sPaginationType": "full_numbers",
                data: RowN
                });
    }  else { // le Node n'as pas de command_class
        var thOut =[];
        thOut[0]="No Command_Class";
        console.log("Dans createValuesTab no Cmd-Class : " + thOut);
    };
};

function renderCmdClssStatus(data, type, full, meta) {
    var api = $.fn.dataTable.Api(meta.settings);
    var cell = api.cell(meta.row, 0);
    var refId = cell.data().split(".");
    var valueData = GetValueZWNode(refId[0],refId[1],refId[2]);
    var valueRef = GetValueRefId(refId[0],refId[1],refId[2]);
    if (valueData) {
        if (valueData.readOnly==true) {
            textRW = "Read only";
            st ='active';
        } else {            
            textRW = "Read and Write";
            st ='inactive';
        };
        var rw=  " <span id='st"+valueRef +"' class='icon16-text-right icon16-status-" + st +"' title='" + textRW + "'></span>";
        if (valueData.help!="") {
            extra = "  <span id='hn"+valueRef +"' class='icon16-text-right icon16-status-info' title='" + valueData.help + "'></span>";
        } else {
            extra ="";
        };
        if (valueData.domogikdevice) { //Available for domogik device
            textstatus = "Named domogik device : " + valueData.domogikdevice.networkid + "." +valueData.domogikdevice.node+"."+valueData.domogikdevice.instance;
            st = 'primary';
        } else { //not available
            textstatus = "Not available for domogik device";
            st = 'false';
        };
        if (valueData.polled) { 
            poll = " checked='checked'";
            tpoll = "Value is polled with intensity : " + valueData.pollintensity;
        }else { 
            poll ="";
            tpoll =  "Check to poll this value";
        }

        return  "<span  id='adr"+valueRef +"'class='icon16-text-right icon16-status-" + st + "' title='" + textstatus +
                "'></span>" + rw + "<input type='checkbox' class='medium' id='poll" + valueRef + "'" + poll + " name='isPolled'" +
                "title='"+ tpoll + "' />" + extra;
    } else {
        return "No data :(";
    };
};

function renderCmdClssValue(data, type, full, meta) {
    var api = $.fn.dataTable.Api(meta.settings);
    var cell = api.cell(meta.row, 0);
    var refId = cell.data().split(".");
    var valueData = GetValueZWNode(refId[0],refId[1],refId[2]);
    var valueRef = GetValueRefId(refId[0],refId[1],refId[2]);
    if (valueData) {
        var id = "valCC" + valueRef;
        if (valueData.realvalue == undefined) {valueData.realvalue = valueData.value; };
        var modify =  (valueData.realvalue != valueData.value);
        var ret = valueData.value;
        if (valueData.readOnly==true) {
            ret = "<span id='" + id +"' title=''>" +  valueData.value+ "</span>";
        } else {            
            if (valueData.type=='Bool') {
                opt="";
                valueData.realvalue = (valueData.realvalue == 'true');
                valueData.value = (valueData.value == 'true');
                modify =  (valueData.realvalue != valueData.value);
                if (valueData.label.search(/switch/i) != -1) {
                    var state = '';
                    if (valueData.value) { state = ' checked'};
                    ret = "<div class='make-switch'>"
                    ret += "<input id='" + id + "' name='CmdClssValue' type='checkbox'" + state + ">";
                    ret += "</div>"
                } else {
                    if (valueData.value) {
                        opt = "<option selected value=" + valueData.value +">" + valueData.value + "</option>" +
                                 "<option value=false>false</option>";
                    } else {
                        opt = "<option value=true>true</option>" +
                                 "<option selected value=" + valueData.value +">" + valueData.value + "</option>" ;
                    }
                    ret ="<select id='" + id + "' name='CmdClssValue' class='listes ccvalue' style='width:7em' title=''>" + opt + "</select>";
                };
            };
            if (valueData.type=='Byte') {
                ret ="<input id='" + id + "' name='CmdClssValue' class='form-control input-sm' type='number' min='0' max='255' value='"+ valueData.value +"' title=''></input>";
                };
            if (valueData.type=='Short') {
                ret ="<input id='" + id + "' name='CmdClssValue' class='form-control input-sm' type='number' min='0' max='65535' value='"+ valueData.value +"' title=''></input>";
            };
            if (valueData.type=='Int' | valueData.type=='Decimal') {
                ret ="<input id='" + id + "' name='CmdClssValue' class='form-control input-sm' type='number' value='"+ valueData.value +"' title=''></input>";
            };
            if (valueData.type=='String') {
//                ret ="<input id='" + id + "' name='CmdClssValue' class='ccvalue' type='text' value='"+ valueData.value +"' title=''></input>";
                ret = renderInputText( id, "valueN", "value", valueData.value, "");
            };
             if (valueData.type=='Schedule') {
                ret ="<input id='" + id + "' name='CmdClssValue' class='ccvalue' type='date' value='"+ valueData.value +"' title=''></input>";
            };
             if (valueData.type=='List') {
//                opt="";
//                 for (i in valueData.listElems) {
//                     if (valueData.listElems[i] != valueData.value) {
//                        opt= opt + "<option value='" + valueData.listElems[i]  + "'>" + valueData.listElems[i] + "</option>";
//                     } else {
//                        opt= opt + "<option selected value='" + valueData.value +"'>" + valueData.value + "</option>";
//                     }
//                 }
//                ret ="<select id='" + id + "' name='CmdClssValue' class='liste ccvalue' style='width:15em' title=''>" + opt + "</select>";
                
                ret = "<select class='form-control input-sm' id='"+id+"' name='CmdClssValue'>"
                for (i in valueData.listElems) {
                    ret += "<option value='"+ valueData.listElems[i] +"'"
                    if (valueData.listElems[i] == valueData.value) {
                        ret += " selected"
                    };
                    ret += ">" + valueData.listElems[i] + "</option>"
                };
                ret += "</select>"
            };
            if (valueData.type=='Button') {
                ret ="<input id='" + id + "' name='CmdClssValue' class='ccvalue ccbt' type='button' value='" + valueData.label +"' title=''></input>"; //
            };
            if (modify) {
                ret = ret + "<button id='send" + valueRef +"' class='button icon16-action-update buttonicon' name='Send value' title='Send value'><span class='offscreen'>Send value</span></button>";
            };
        };
        return ret
    } else {
        return "No data :(";
    };
};

function renderCmdClssName(data, type, full, meta) {
    var api = $.fn.dataTable.Api(meta.settings);
    var cell = api.cell(meta.row, 0);
    var refId = cell.data().split(".");
    var valueData = GetValueZWNode(refId[0],refId[1],refId[2]);
    var valueRef = GetValueRefId(refId[0],refId[1],refId[2]);
    if (valueData) {
        return   "<span id='hc"+valueRef +"'title='" + valueData.help + "'>" + valueData.commandClass + "</span>";
    } else {
        return "No data :(";
    };
};
