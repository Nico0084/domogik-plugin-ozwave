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

function GetValueCell(table, valueRef, col) {
    try {
        var row = $("#value"+ valueRef)[0].parentNode;
        var index = table.cell(row).index();
        var cell = table.cell(index.row, col);
        }
    catch (err) {
        var cell = false;
        };
    return cell
};

function validateSetValueCmdClss(refId, newValue, valueData) {
    if (valueData.genre != "User") {
        bootbox.confirm('<p class="text-center">Set Command Class value for Node ' + valueData.nodeId + ', instance ' + valueData.instance +', <b>' + valueData.label +
            '</b> to </p><h4 class="text-center">' + newValue + '</h4>',
        function(result) {
            if (result) {
                setValueCmdClss(refId, newValue);
            } else {
                var table = $('#valuesNode' + GetNodeRefId(refId[1],refId[2])).DataTable();
                var cell = GetValueCell(table, GetValueRefId(refId[1],refId[2],refId[3]), 3);
                cell.data(valueData.value).draw('page');
            };
        });
    } else {
        setValueCmdClss(refId, newValue);
    };
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
            "drawCallback": function(settings) {
                var api = this.api();
                var data = api.rows({page:'current'}).data()
                // activate poll checkbox
                $( "[id^='poll_']").not("[isHandled]" ).each(function(rowN, nData) {
                    var refId =  this.id.split("_");
                    var valueData = GetValueZWNode(refId[1],refId[2],refId[3]);
                    $(this).attr("isHandled", true);
                    $(this).click(function(e){
                        var polled = ''
                        if  (valueData.polled) {
                            polled='checked';
                            $(this).prop('checked', true);
//                            $(this).attr('checked', 'checked');
                        } else {
                            $(this).prop('checked', false);
                        };
                        var delay = '';
                        if (valueData.pollintensity == 0) {valueData.pollintensity = 1};
                        if (ozwInfo.Options.IntervalBetweenPolls.value) {
                            delay = "Approx every " + (ozwInfo.Options.PollInterval.value/valueData.pollintensity) + " msec";
                        } else  {
                            delay = "Every " + ((ozwInfo.Options.PollInterval.value/1000)/valueData.pollintensity) + " sec";
                        };
                        var bdiag = bootbox.dialog({
                            show: false,
                            size: 'small',
                            className: 'text-center',
                            title: 'Set polling value for <b>'+  valueData.label  +'</b> instance <b>'+ valueData.instance + '</b> node <b>'+ refId[1]+ '.' + refId[2] + '<b>',
                            message: "<div class='row'>" +
                                            "<p>" + valueData.commandClass + "</p>" +
                                            "<p>Set if value must be polled and his instensity.</p>" +
                                            "<h4>Global pool parameters :</h4><ul>"  +
                                                "<li class='text-left' title='"+ ozwInfo.Options.PollInterval.doc +"'>Interval : " + ozwInfo.Options.PollInterval.value + " msec</li>" +
                                                "<li class='text-left' title='"+ ozwInfo.Options.IntervalBetweenPolls.doc +"'>Interval Between Polls: " + ozwInfo.Options.IntervalBetweenPolls.value + "</li></ul>" +
                                            "<h5 class='alert-info'>Save openzwave network configuration to keep change.</h5>" +
                                          "</div>" +
                                          "<div class='row'>" +
                                            "<div class='col-md-12'> " +
                                                "<label for='intensity'>Intensity</label>" +
                                                "<div class='input-group'>"+
                                                    "<span class='input-group-addon'>Polled " +
                                                        "<input id='polled' type='checkbox'"+ polled + ">" +
                                                    "</span>" +
                                                    "<input id='intensity' type='number' class='form-control' value=" + valueData.pollintensity + ">" +
                                                "</div>" +
                                            "</div>" +
                                          "</div>" +
                                          "<div class='row'>" +
                                            "<p id='delay'>"+ delay +"</p>" +
                                          "</div>",
                            data: valueData,
                            buttons: [{
                                id: 'btn-cancel',
                                label: 'Cancel',
                                className: 'btn-danger',
                                autospin: false,
                                callback: function(dialogRef){
//                                    console.log("Cancel set polling value : " + refId[1]+ "." + refId[2]);
                                }
                            },{
                                id: 'btn-ok',
                                label: 'Ok',
                                className: 'btn-primary',
                                autospin: false,
                                callback: function(dialogRef){
//                                    console.log("Send set polling value : " + refId[1]+ "." + refId[2]);
                                    var action = 'DisablePoll';
                                    if ($('#polled').is(':checked')) { action = 'EnablePoll';}
                                    var intensity  = $('#intensity').val();
                                    sendRequest("ozwave.value.poll", {"action": action, "networkId": refId[1], "nodeId": refId[2], "valueId": refId[3],
                                                      "intensity": intensity}, function(data, result) {
                                        if (result == "error" || data.result == "error") {
                                            new PNotify({
                                                type: 'error',
                                                title: 'Poll action ' + data.content.action + ' fail.',
                                                text: data.content.error,
                                                delay: 6000
                                            });
                                        } else {
                                            var table = $('#valuesNode' + GetNodeRefId(data.content.NetworkID,data.content.NodeID)).DataTable();
                                            var valueData = GetValueZWNode(data.content.NetworkID, data.content.NodeID, data.content.ValueID);
                                            var valueRef = GetValueRefId(data.content.NetworkID, data.content.NodeID, data.content.ValueID);
                                            valueData.pollintensity = data.content.intensity;
                                            if (data.content.action == "EnablePoll") {
                                                valueData.polled = true;
                                                $('#poll'+valueRef).attr('title',"Value is polled with intensity : " + valueData.pollintensity).prop('checked', true);
                                            } else {
                                                valueData.polled = false;
                                                $('#poll'+valueRef).attr('title', "Check to poll this value").prop('checked', false) ;
                                            };
                                            RefreshValueNodeData(data.content.NetworkID, data.content.NodeID, valueData);
                                            var cell = GetValueCell(table, GetValueRefId(data.content.NetworkID, data.content.NodeID, data.content.ValueID), 0);
                                            HighlightCell(cell.node());
                                        };
                                    });
                                }
                            }]
                        });
                        $("#intensity").on('change', function(e) {
                            var delay = '';
                            if (ozwInfo.Options.IntervalBetweenPolls.value) {
                                delay = "Approx every " + (ozwInfo.Options.PollInterval.value/this.value) + " msec";
                            } else  {
                                delay = "Every " + ((ozwInfo.Options.PollInterval.value/1000)/this.value) + " sec";
                            };
                            $("#delay").text(delay);
                        });
                        bdiag.modal('show');
                    });
                });

                // activate inputs
                $( "[name='CmdClssValue']").not("[isHandled]" ).each(function(rowN, nData) {
                    var refId =  this.id.split("_");
                    var valueData = GetValueZWNode(refId[1],refId[2],refId[3]);
                    $(this).attr("isHandled", true);
                    switch (valueData.type) {
                        case 'Bool' :
                            if ($(this).hasClass("switchtype")) {
                                $(this).bootstrapSwitch()
                                $(this).on('switchChange.bootstrapSwitch', function (event, state) {
                                    validateSetValueCmdClss(refId, state, valueData);
                                });
                            };
                            break;
                        case 'Byte' :
                        case 'Short' :
                        case 'Int' :
                        case 'Decimal' :
                            $(this).on('keypress keyup change', function (e) {
                                if (e.type == 'keypress') {
                                    if (e.which == 13) {
                                        var value = this.value;
                                        validateSetValueCmdClss(refId, value, valueData);
                                        return false;
                                    };
                                };
                                var valueRef = GetValueRefId(refId[1],refId[2],refId[3]);
                                if (valueData.realvalue.toString() != this.value) {
                                    $("#stch"+ valueRef).removeClass('hidden');
                                } else {
                                    $("#stch"+ valueRef).addClass('hidden');
                                };
                                if (e.which == 13) {return false};
                            });
                            break;
                        case 'List' :
                            $(this).on('change', function(e) {
                                var value = this.value;
                                validateSetValueCmdClss(refId, value, valueData);
                            });
                            break;
                        case 'String' :
                            EnableInputText(this, function(obj) {
                                var value = obj.value;
                                validateSetValueCmdClss(refId, value, valueData);
                            });
                            break;
                        case 'Button' :
                            $(this).on('click', function () {
                                var value =$(this).val();
                                validateSetValueCmdClss(refId, value, valueData);
//                                var $btn = $(this).button('loading')
//                                // business logic...
//                                $btn.button('reset')
                              })
                            break;
                    };
                });
            },
        "sPaginationType": "full_numbers",
        data: RowN
        });
    }  else { // le Node n'as pas de command_class
        var thOut =[];
        thOut[0]="No Command_Class";
//        console.log("Dans createValuesTab no Cmd-Class : " + thOut);
    };
};

function renderCmdClssStatus(data, type, full, meta) {
    var api = $.fn.dataTable.Api(meta.settings);
    var cell = api.cell(meta.row, 0);
    var refId = cell.data().split(".");
    var valueData = GetValueZWNode(refId[0],refId[1],refId[2]);
    var valueRef = GetValueRefId(refId[0],refId[1],refId[2]);
    if (valueData) {
        var st = "<i class='fa fa-upload icon-success'></i>";
        var textRW = "Read only";
        if (valueData.readOnly == false) {
            textRW = "Read and Write";
            st += "<i class='fa fa-download'></i>";
        };
        var rw = " <span id='st"+valueRef +"' class='extbtn' title='" + textRW + "'>" + st +"</span>";
        var extra ="";
        if (valueData.help!="") {
            extra = "  <span id='hn"+valueRef +"' class='fa fa-info-circle fa-lg extbtn icon-info' title='" + valueData.help + "'></span>";
        };
        var textstatus = "Not available for domogik device";
        var st = 'fa-ban icon-warning';
        if (valueData.domogikdevice) { //Available for domogik device
            textstatus = "Domogik device parameters: \n" +
                         "  networkid: " + valueData.domogikdevice.networkid + "\n" +
                         "  node: " + valueData.domogikdevice.node + "\n" +
                         "  instance: " + valueData.domogikdevice.instance + "\n" +
                         "  dmg label: " + valueData.domogikdevice.label;
            st = 'fa-star icon-success';
        };
        var poll ="";
        var tpoll =  "Check to poll this value.";
        if (valueData.polled) {
            poll = " checked";
            tpoll = "Value is polled with intensity : " + valueData.pollintensity;
        };

        return  "<span id='value"+valueRef +"'class='fa extbtn " + st + "' title='" + textstatus +
                "'></span>" + rw + extra + "<input type='checkbox' class='medium' id='poll" + valueRef + "'" + poll + " name='isPolled'" +
                "title='"+ tpoll + "' />";
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
        var modify = "";
        if (valueData.realvalue == undefined) {
                valueData.realvalue = valueData.value;
                modify = '<span class="input-addon-xs label-warning"><i id="stic_'+ valueRef +'" class="fa fa-warning" title="Value not confirmed by node."> Not recovered</i></span>';
        } else if (valueData.realvalue != valueData.value) {
            modify = '<span class="input-addon-xs label-warning"><i id="stic_'+ valueRef +'" class="fa fa-warning" title="Value change but not confirmed by node."> old : ' + valueData.realvalue + '</i></span>';
        };
        var ret = valueData.value;
        if (valueData.readOnly==true) {
            ret = "<span id='" + id +"' title=''>" +  valueData.value+ "</span>";
        } else {
            switch (valueData.type) {
                case 'Bool' :
                    if (valueData.label.search(/switch/i) != -1) {
                        var state = '';
                        if (valueData.value) { state = ' checked'};
                        ret = "<div class='make-switch'>";
                        ret += "<input id='" + id + "' name='CmdClssValue' type='checkbox' class='switchtype'" + state + ">";
                        ret += modify + "</div>";
                    } else {
                        var opt="";
                        if (valueData.value) {
                            opt = "<option selected value=" + valueData.value +">" + valueData.value + "</option>" +
                                     "<option value=false>false</option>";
                        } else {
                            opt = "<option value=true>true</option>" +
                                     "<option selected value=" + valueData.value +">" + valueData.value + "</option>" ;
                        }
                        ret ="<select id='" + id + "' name='CmdClssValue' class='listes ccvalue' style='width:7em' title=''>" + opt + "</select>";
                    };
                    break;
                case 'Byte' :
                case 'Short' :
                case 'Int' :
                case 'Decimal' :
                    ret = "<div class='input-group'><span class='input-group-addon label-warning hidden' id='stch"+ valueRef +
                            "' title='Value is actually "+valueData.realvalue+". You must validate your change by enter key.'><i class='fa fa-recycle'></i></span>";
                    ret +="<input id='" + id + "' name='CmdClssValue' class='form-control input-sm' type='number' aria-describedby='stch"+ valueRef + "' min='" +
                            valueData.min  +" ' max='"+ valueData.max  +"' value='"+ valueData.value +"' title='range "+valueData.min+" to "+valueData.max+"'></input>" +
                            modify + "</div>";
                    break;
                case 'Raw' :
                case 'String' :
                    ret = renderInputText( id, "valueN", "value", valueData.value, "");
                    break;
                case 'Schedule' :
                    ret ="<input id='" + id + "' name='CmdClssValue' class='ccvalue' type='date' value='"+ valueData.value +"' title=''></input>";
                    break;
                case 'List' :
                    ret = "<div class='input-group'>";
                    ret += "<select class='form-control input-sm' id='"+id+"' name='CmdClssValue'>"
                    for (i in valueData.listelems) {
                        ret += "<option value='"+ valueData.listelems[i] +"'"
                        if (valueData.listelems[i] == valueData.value) {
                            ret += " selected"
                        };
                        ret += ">" + valueData.listelems[i] + "</option>"
                    };
                    ret +="</select>" + modify + "</div>";
                    break;
                case 'Button' :
                    ret ="<button id='" + id + "' name='CmdClssValue' class='btn btn-default btn-xs' type='button' value='" + valueData.label +"' title=''>"+ valueData.label +"</v>";
                    break;
                default :
                    ret = "No data :(";
            };
        };
    };
    return ret;
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
