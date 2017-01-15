// Xonomy xml document specification

Xonomy.askStringInfo=function(defaultString, params) {
    var html="";
    if (params != undefined && params.help!= undefined && params.help != "") {
        html +="<i class='fa fa-info-circle fa-lg icon-info' style='margin:2px 5px' title='" + params.help + "'></i>";
    };
    if (params != undefined && params.title!= undefined && params.title != "") {
        html = "<p>"+html+"<span><b>"+params.title+"</b></span></p>";
    };
    html+=Xonomy.askString(defaultString);
    return html;
};

Xonomy.askLongStringInfo=function(defaultString, params) {
    var html="";
    if (params != undefined && params.help!= undefined && params.help != "") {
        html +="<i class='fa fa-info-circle fa-lg icon-info' style='margin:2px 5px' title='" + params.help + "'></i>";
    };
    if (params != undefined && params.title!= undefined && params.title != "") {
        html = "<p>"+html+"<span><b>"+params.title+"</b></span></p>";
    };
    html+=Xonomy.askLongString(defaultString);
    return html;
};

Xonomy.askPicklistInfo=function(defaultString, params) {
    var html="";
    if (params != undefined && params.help!= undefined && params.help != "") {
        html +="<i class='fa fa-info-circle fa-lg icon-info' style='margin:2px 5px' title='" + params.help + "'></i>";
    };
    if (params != undefined && params.title!= undefined && params.title != "") {
        html = "<p>"+html+"<span><b>"+params.title+"</b></span></p>";
    };
    html+=Xonomy.askPicklist(defaultString, params.pickList);
    return html;
};

function xonomyValidate_Int(jsAttribute) {
    if($.trim(jsAttribute.value)=="") {
        Xonomy.warnings.push({htmlID: jsAttribute.htmlID, text: "The @"+jsAttribute.name+" attribute should not be undefine."});
        return false;
    } else if (!Number.isInteger(Number(jsAttribute.value))) {
        Xonomy.warnings.push({htmlID: jsAttribute.htmlID, text: "The @"+jsAttribute.name+" attribute should be a integer."});
        return false;
    };
    return true;
};

var xmlDocSpec = {
    elements: {
        "Manufacturer": {
            mustBeBefore: ["CommandClasses"],
            attributes: {
                "name": {
                asker: Xonomy.askString
                }
            }
        },
        "CommandClass": {
            attributes: {
                "id": {
                    asker: Xonomy.askStringInfo,
                    askerParameter: {"title": 'Command Class identification number',
                                    "help": 'Command class instance of this value. It is possible for there to be '+
                                                'multiple instances of a command class, although currently it appears that '+
                                                'only the SensorMultilevel command class ever does this.  Knowledge of '+
                                                'instances and command classes is not required to use OpenZWave, but this  '+
                                                'information is exposed in case it is of interest.'},
					validate: function(jsAttribute){
                        return xonomyValidate_Int(jsAttribute);
                    }
                },
                "name": {
                    asker: Xonomy.askStringInfo,
                    askerParameter: {"title": 'Command Class identification name',
                                    "help": 'Command class full name according to command class id.'+
                                            'Refer to zwave specification.'},
					validate: function(jsAttribute){
                        // TODO : Check if name is correct.
                        return true;
                    }
                },
                "version": {
                    asker: Xonomy.askStringInfo,
                    askerParameter: {"title": 'Command Class version number',
                                    "help": 'Refer to manufacturer user manual. default <1>'},
					validate: function(jsAttribute){
                        return xonomyValidate_Int(jsAttribute);
                    }
                },
                "request_flags": {
                    asker: Xonomy.askPicklistInfo,
                    askerParameter: {
                        "title": 'Select bit compose for request at start-up',
                        "pickList": [
                            {value: "1", caption: "Request Instance."},
                            {value: "2", caption: "Request Values."},
                            {value: "4", caption: "Request Version."},
                            {value: "3", caption: "Request Instance & Values."},
                            {value: "5", caption: "Request Instance & Version."},
                            {value: "6", caption: "Request Values & Version."},
                            {value: "7", caption: "Request Instance & Values & Version."}
                        ]
                    }
                },
                "override_precision": {
                    asker: Xonomy.askStringInfo,
                    askerParameter: {"title": 'Override value precision',
                                     "help": 'Override precision when writing values if >=0'},
					validate: function(jsAttribute){
                        return xonomyValidate_Int(jsAttribute);
                    }
                },
                "after_mark": {
                    asker: Xonomy.askPicklistInfo,
                    askerParameter: {
                        "title": 'No controled command class',
                        "help":  'Set to true if the command class is listed after COMMAND_CLASS_MARK, and should not create any values.',
                        "pickList": ["true", "false"]
                    }
                },
                "create_vars": {
                    asker: Xonomy.askPicklistInfo,
                    askerParameter: {
                        "title": 'Do we want to create variables',
                        "help":  'Create or not depending values of command class.'+
                                     'If attribute @create_vars not present openzwave use default True.',
                        "pickList": ["true", "false"]
                    }
                },
                "getsupported": {
                    asker: Xonomy.askPicklistInfo,
                    askerParameter: {
                        "title": 'Get operation supported',
                        "help":  'Handle or not request values of command class.'+
                                     'If attribute @getsupported not present openzwave use default True.',
                        "pickList": ["true", "false"]
                    }
                },
                "issecured": {
                    asker: Xonomy.askPicklistInfo,
                    askerParameter: {
                        "title": 'Command class secured',
                        "help":  'Is this command class secured with the Security Command Class.'+
                                     'If attribute @issecured not present openzwave use default false.',
                        "pickList": ["true", "false"]
                    }
                },
                "innif": {
                    asker: Xonomy.askPicklistInfo,
                    askerParameter: {
                        "title": 'Present in the NIF Frame',
                        "help":  'Was this command class present in the NIF Frame we recieved '+
                                      'or was it created from our device_classes.xml file, or because it was in the Security SupportedReport message.',
                        "pickList": ["true", "false"]
                    }
                },
                "mapping": {
                    asker: Xonomy.askStringInfo,
                    askerParameter: {"title": 'Mapping Command Class id number',
                                    "help": 'Genraly used by Basic command class to mappe towards an other.'},
					validate: function(jsAttribute){
                        return xonomyValidate_Int(jsAttribute);
                    }
                }
            }
        },
        "Instance": {
            mustBeBefore: ["Value", "Associations"]
        },
        "Value": {
            mustBeBefore: ["SensorMap"],
            menu: [{
                caption: "Add @size=\"0\"",
                action: Xonomy.newAttribute,
                actionParameter: {name: "size", value: "0"},
                hideIf: function(jsElement){
                    return jsElement.hasAttribute("size");
                }
                }, {
                caption: "Delete this <Value>",
                action: Xonomy.deleteElement
                }, {
                caption: "New <Value> before this",
                action: Xonomy.newElementBefore,
                actionParameter: "<Value type='' genre='' instance='1' index='' label=''/>"
                }, {
                caption: "New <Value> after this",
                action: Xonomy.newElementAfter,
                actionParameter: "<Value type='' genre='' instance='1' index='' label=''/>"
                }],
            attributes: {
                "type": {
                    asker: Xonomy.askPicklistInfo,
                    askerParameter: {
                        "title": 'Select type of data represented by the value object.',
                        "pickList": [
                            {value: "bool", caption: "Boolean, true or false."},
                            {value: "button", caption: "A write-only value that is the equivalent of pressing a button."},
                            {value: "byte", caption: "8 bits"},
                            {value: "short", caption: "16-bit signed value."},
                            {value: "int", caption: "32-bit signed value."},
                            {value: "decimal", caption: "Represents a non-integer value as a string, to avoid floating point accuracy issues."},
                            {value: "string", caption: "Text string."},
                            {value: "list", caption: "List from which one item can be selected."},
                            {value: "Schedule", caption: "Complex type used with the Climate Control Schedule command class."},
                            {value: "Raw", caption: "A collection of bytes."}
                            ]
                        },
					validate: function(jsAttribute) {
						if($.trim(jsAttribute.value)=="") {
							Xonomy.warnings.push({htmlID: jsAttribute.htmlID, text: "The @type attribute should not be undefine."});
							return false;
						}
						return true;
					}
                },
                "genre": {
                    asker: Xonomy.askPicklistInfo,
                    askerParameter: {
                        "title": 'Select classification of a value',
                        "help": 'This attribute enable low level system or configuration parameters to be filtered by the application.',
                        "pickList": [
                            {value: "basic", caption: "The 'level' as controlled by basic commands."},
                            {value: "user", caption: "User would be interested in."},
                            {value: "config", caption: "Device-specific configuration parameters."},
                            {value: "system", caption: "Only to users who understand the Z-Wave protocol."}
                            ]
                    },
					validate: function(jsAttribute) {
						if($.trim(jsAttribute.value)=="") {
							Xonomy.warnings.push({htmlID: jsAttribute.htmlID, text: "The @genre attribute should not be undefine."});
							return false;
						}
						return true;
					}
                },
                "instance": {
                    asker: Xonomy.askStringInfo,
                    askerParameter: {"title": 'Value identification instance',
                                                    "help": 'It is possible for there to be multiple instances of a command class, ' +
                                                            'although currently it appears that only the SensorMultilevel command class ever does this. '+
                                                            'Knowledge of instances and command classes is not required to use OpenZWave, '+
                                                            'but this information is exposed in case it is of interest.'},
					validate: function(jsAttribute) {
						if($.trim(jsAttribute.value)=="") {
							Xonomy.warnings.push({htmlID: jsAttribute.htmlID, text: "The @instance attribute should not be undefine."});
							return false;
						} else if (!Number.isInteger(Number(jsAttribute.value))) {
							Xonomy.warnings.push({htmlID: jsAttribute.htmlID, text: "The @instance attribute should be a integer."});
							return false;
                        };
						return true;
					}
                },
                "index": {
                    asker: Xonomy.askStringInfo,
                    askerParameter: {"title": 'Value identification index',
                                                 "help": 'The index is used to identify one of multiple ' +
                                                        'values created and managed by a command class.  In the case of configurable ' +
                                                        'parameters (handled by the configuration command class), the index is the '+
                                                        'same as the parameter ID.  Knowledge of command classes is not required '+
                                                        'to use OpenZWave, but this information is exposed in case it is of interest.'},
					validate: function(jsAttribute) {
						if($.trim(jsAttribute.value)=="") {
							Xonomy.warnings.push({htmlID: jsAttribute.htmlID, text: "The @index attribute should not be undefine."});
							return false;
						} else if (!Number.isInteger(Number(jsAttribute.value))) {
							Xonomy.warnings.push({htmlID: jsAttribute.htmlID, text: "The @index attribute should be a integer."});
							return false;
                        };
						return true;
					}
                },
                "label": {
                    asker: Xonomy.askStringInfo,
                    askerParameter: {"title": 'Enter your label'},
					validate: function(jsAttribute) {
						if($.trim(jsAttribute.value)=="") {
							Xonomy.warnings.push({htmlID: jsAttribute.htmlID, text: "The @label attribute should not be undefine."});
							return false;
                        };
						return true;
					}
                },
                "units":{
                    asker: Xonomy.askStringInfo,
                    askerParameter: {"title": 'Enter value unit'},
                },
                "read_only":{
                    asker: Xonomy.askPicklistInfo,
                    askerParameter: {
                        "title": 'Access type',
                        "help":  'This value is only on read from zwave device',
                        "pickList": ["true", "false"]
                    }
                },
                "write_only":{
                    asker: Xonomy.askPicklistInfo,
                    askerParameter: {
                        "title": 'Access type',
                        "help":  "This value is only on write from zwave device."+
                                     " Variable cannot be retrieved to know his real value.",
                        "pickList": ["true", "false"]
                    }
                },
                "verify_changes": {
                    asker: Xonomy.askPicklistInfo,
                    askerParameter: {
                        "title": 'Verify value changed',
                        "pickList": ["true", "false"]
                    }
                },
                "poll_intensity": {
                    asker: Xonomy.askStringInfo,
                    askerParameter: {
                        "title": 'Polling Intensity',
                        "help":  "Number of poll during global PollInterval config parameter."+
                                     " value '0' desactivate polling."
                    },
                    validate: function(jsAttribute){
                        return xonomyValidate_Int(jsAttribute);
                    }
                }
            }
        },
        "Help": {
            mustBeBefore: ["Item"],
            asker: Xonomy.askLongStringInfo,
            askerParameter: {"title": 'Enter description, generaly from manufacturer manual.',
                                        "help":'For test :-)'},
        }
    },
    validate: function(jsElement){
        //Validate the element:
        var elementSpec=xmlDocSpec.elements[jsElement.name];
        if(elementSpec.validate) elementSpec.validate(jsElement);
        //Cycle through the element's attributes:
        for(var i=0; i<jsElement.attributes.length; i++) {
            var jsAttribute=jsElement.attributes[i];
            var attributeSpec=elementSpec.attributes[jsAttribute.name];
            if(attributeSpec.validate) attributeSpec.validate(jsAttribute);
        };
        //Cycle through the element's children:
        for(var i=0; i<jsElement.children.length; i++) {
            var jsChild=jsElement.children[i];
            if(jsChild.type=="element") { //if element
                xmlDocSpec.validate(jsChild); //recursion
            }
        }
    }
};

function initValuesTab(refId, nodeData) {
    var nodeRef = GetNodeRefId(nodeData.NetworkID, nodeData.NodeID);
    var struct = '<div class="contenaire-fluid">'+
            '<div class="panel panel-default">'+
                '<div class="panel-heading\">'+
                    '<a class="bg-info" href="#" onclick="togglePanelCollapse(this);return false;" body="nodeInfo_'+refId+'"' + ' toggle="togglenodeInfo_'+refId+'">'+
                        '<h5>' + ' Details for : ' + nodeData.Infos.basic.label + ' - ' + nodeData.Infos.generic.label + ' - ' + nodeData.Infos.specific.label +
                            '<span class="glyphicon glyphicon-chevron-down pull-left" id="togglenodeInfo_'+refId+'" aria-hidden="true" data-target="nodeInfo_'+refId+'"> </span>' +
                        '</h5>'+
                    '</a>'+
                '</div>'+
                '<div class="panel-body" id="nodeInfo_'+refId+'" style="width: 95%; display: none;" hidden>'+
                    '<div class="row text-center">'+
                        '<span class="btn btn-info" id="xmlnodeconfig'+ nodeRef +'">' +
                            '<i id="xmlnodeconf-ic'+ nodeRef +'" class="fa fa-info-circle"></i>' +
                            '<span> Display xml data form openzwave config ...</span>' +
                        '</span>'+
                    '</div>'+
                    '<div class="row">'+
                        '<div class="pre-scrollable" id="xmlconfig'+nodeRef+'">'+'</div>' +
                    '</div>'+
                    '<div class="row">'+
                        '<div class="col-md-8">'+
                            '<h4>Device type</h4>'+
                            '<ul>'+
                                '<li>Type : <b>'+nodeData.Type+'</b></li>'+
                                '<li>Basic : <b><i>'+ nodeData.Infos.basic.key + '</i> - ' + nodeData.Infos.basic.label +'</b></li>';
    if (nodeData.Infos.basic.command_classes.length > 0) {
        struct += '<ul>Associate with : ';
        for (clss in nodeData.Infos.basic.command_classes) {
            struct += '<li>'+nodeData.Infos.basic.command_classes[clss]+'</li>';
        };
        struct += '</ul>';
    };
              struct += '<li>Generic : <b><i>'+ nodeData.Infos.generic.key + '</i> - ' + nodeData.Infos.generic.label +'</b></li>'
    if (nodeData.Infos.generic.command_classes.length > 0) {
        struct += '<ul>Associate with : ';
        for (clss in nodeData.Infos.generic.command_classes) {
            struct += '<li>'+nodeData.Infos.generic.command_classes[clss]+'</li>';
        };
        struct += '</ul>';
    };
               struct +='<li>Specific : <b><i>'+ nodeData.Infos.specific.key + '</i> - ' + nodeData.Infos.specific.label +'</b></li>';
    if (nodeData.Infos.specific.command_classes.length > 0) {
        struct += '<ul>Associate with : ';
        for (clss in nodeData.Infos.specific.command_classes) {
            struct += '<li>'+nodeData.Infos.specific.command_classes[clss]+'</li>';
        };
        struct += '</ul>';
    };
          struct += '</ul></div>'+
                        '<div class="col-md-4">'+
                        '<h4>Network capabilities</h4>'+
                        '<ul>'+
                            '<li>Maximum baud rate : <b>'+ nodeData.Infos.maxBaudRate + '</b> bps</li>'+
                            '<li>Protocol version : <b>'+ nodeData.Infos.version + '</b></li>'+
                            '<li>Security flag : <b>'+ nodeData.Infos.security + '</b></li>'+
                            '<li>Zwave + : ';
    if (nodeData.Infos["zwave +"]) {
            struct += '<span class="fa fa-plus-square icon-success" </span></li>' +
                        '</ul></div></div>'+
                        '<div class="row">'+
                            '<div class="col-md-6">'+
                            '<h4>Zwave + extra infos</h4>'+
                            '<ul>'+
                                '<li>Device type : <b><i>'+nodeData.Infos["info +"].deviceType+'</i> - '+nodeData.Infos["info +"].deviceTypeName+'</b></li>'+
                                '<li>Type + : <b><i>'+nodeData.Infos["info +"].plusType+'</i> - '+nodeData.Infos["info +"].plusTypeStr+'</b></li>'+
                                '<li>Role : <b><i>'+nodeData.Infos["info +"].role+'</i> - '+nodeData.Infos["info +"].roleName+'</b></li>';
    } else {struct += '<span class="fa fa-minus-square icon-warning" </span></li>';};

    struct += '</ul></div>';
    struct +=  '</div>'+
                '</div>'+
            '</div>';

     struct += '<table id="valuesNode'+refId+'" class="display cell-border" cellspacing="0" width="100%">'+
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
                   '</div>';
    return struct;
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

function enableXmlConfigEdit(){
    console.log(data.content);
    $("[id^='xmlnodeconfig']").not("[isHandled]" ).each(function(rowN, nData) {
    EnableButtonAction(this, function(obj) {
        $("[id^='xmlnodeconf-ic']").removeClass("fa-info-circle").addClass("fa-spinner fa-spin");
        var refId =  obj.id.split("_");
        var NetworkID = refId[1];
        var NodeID = refId[2];
        var nodeRefId = GetNodeRefId(NetworkID, NodeID);
        sendRequest("ozwave.node.get", {"key": "ozwconfig", "networkId": refId[1], "nodeId": refId[2]}, function(data, result) {
            var nodeRefId = GetNodeRefId(data.content.NetworkID, data.content.NodeID);
            $("[id^='xmlnodeconf-ic']").removeClass("fa-spinner fa-spin").addClass("fa-info-circle");
            if (result == "error" || data.result == "error") {
                new PNotify({
                    type: 'error',
                    title: 'Fail to get xml openzwave config',
                    text: data.content.error,
                    delay: 6000
                });
            } else {
                var editor=document.getElementById("xmlconfig"+nodeRefId);
                Xonomy.render(data.content.xmlSource, editor, xmlDocSpec);
            };
        });
    });
});
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
                $('[data-toggle="tooltip"]').tooltip({
                    html:true
                });
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
                                            "<h4>Global poll parameters :</h4><ul>"  +
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
                                                $('#poll'+valueRef).attr('data-original-title',"Value is polled with intensity : " + valueData.pollintensity).prop('checked', true);
                                            } else {
                                                valueData.polled = false;
                                                $('#poll'+valueRef).attr('data-original-title', "Check to poll this value").prop('checked', false) ;
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
                $( "[id^='reqValRefresh_']").not("[isHandled]" ).each(function(rowN, nData) {
                    var refId =  this.id.split("_");
                    var valueData = GetValueZWNode(refId[1],refId[2],refId[3]);
                    $(this).attr("isHandled", true);
                    $(this).click(function(e){
                        sendRequest("ozwave.value.reqRefresh", {"networkId": refId[1], "nodeId": refId[2], "valueId": refId[3]}, function(data, result) {
                            if (result == "error" || data.result == "error") {
                                new PNotify({
                                    type: 'error',
                                    title: 'Request refreshing value fail.',
                                    text: data.content.error,
                                    delay: 6000
                                });
                            } else {
                                new PNotify({
                                    type: 'success',
                                    title: 'Request refreshing value sended.',
                                    text: data.content.usermsg,
                                    delay: 4000
                                });
                            };
                        });
                    });
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
        var st = "";
        var textRW = "";
        if (!valueData.readOnly) {
            if (!valueData.writeOnly) {
                textRW = "Read and Write";
                st += "<i class='fa fa-upload icon-success'></i><i class='fa fa-download'></i>";
            } else {
                textRW = "Write only";
                st += "<i class='fa fa-download'></i>";
            };
        } else {
            if (!valueData.writeOnly) {
                textRW = "Read only";
                st += "<i class='fa fa-upload icon-success'></i>";
            } else {
                textRW = "Read ? Write ? confilct !";
                st += "<i class='fa fa-upload icon-warning'></i><i class='fa fa-download icon-warning'></i>";
            };
        };
        var rw = " <span id='st"+valueRef +"' class='extbtn' data-toggle='tooltip' data-placement='right' title='" + textRW + "'>" + st +"</span>";
        var extra ="";
        if (valueData.help!="") {
            extra = "  <span id='hn"+valueRef +"' class='fa fa-info-circle fa-lg extbtn icon-info' data-toggle='tooltip' data-placement='right' title='" + valueData.help + "'></span>";
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
        if (!valueData.writeOnly) {
            var poll = "<input type='checkbox' class='medium' id='poll" + valueRef + "' name='isPolled'";
            if (valueData.polled) {
                poll += " checked data-toggle='tooltip' data-placement='right' title='Value is polled with intensity : " + valueData.pollintensity + "' />";
            } else {
                poll += " data-toggle='tooltip' data-placement='right' title='Check to poll this value.'/>";
            };
        } else { var poll = "";};
        return  "<span id='value"+valueRef +"'class='fa extbtn " + st + "' data-toggle='tooltip' data-placement='right' title='" + textstatus +
                "'></span>" + rw + extra + poll;
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
                if (valueData.writeOnly) {
                    modify = '<span class="input-addon-xs label-info"><i id="stic'+ valueRef +
                        '" class="fa fa-warning" data-toggle="tooltip" data-placement="bottom" title="Value not confirmed by node."> '+
                        "Write only, can't recover real value</i>"+
                        '</span>';
                } else {
                    valueData.realvalue = valueData.value;
                    if (valueData.errorRead != "") {var color = " icon-danger";} else {var color = "";};
                    modify = '<span class="input-addon-xs label-warning"><i id="stic'+ valueRef +
                        '" class="fa fa-warning'+color+'" data-toggle="tooltip" data-placement="bottom" title="Value not confirmed by node. '+
                            valueData.errorRead+'"> '+ 'Not recovered</i>'+
                        '<span id="reqValRefresh'+ valueRef + '"class="btn btn-xs btn-info pull-right" data-toggle="tooltip" data-placement="bottom" title="" data-original-title="Request refresh value">'+
                            '<span class="glyphicon glyphicon-refresh"></span>'+
                        '</span>'+
                        '</span>';
                };
        } else if (valueData.realvalue != valueData.value) {
            modify = '<span class="input-addon-xs label-warning"><i id="stic'+ valueRef +
                '" class="fa fa-warning" data-toggle="tooltip" data-placement="bottom" title="Value change but not confirmed by node."> old : ' + valueData.realvalue + '</i></span>';
        };
        var ret = valueData.value;
        if (valueData.readOnly) {
            ret = "<span id='" + id +"' data-toggle='tooltip' data-placement='right' title=''>" +  valueData.value+ "</span>";
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
                        ret ="<select id='" + id + "' name='CmdClssValue' class='listes ccvalue' style='width:7em' data-toggle='tooltip' data-placement='right' title=''>" + opt + "</select>";
                    };
                    break;
                case 'Byte' :
                case 'Short' :
                case 'Int' :
                case 'Decimal' :
                    ret = "<div class='input-group'><span class='input-group-addon label-warning hidden' id='stch"+ valueRef +
                            "' data-toggle='tooltip' data-placement='bottom' title='Value is actually "+valueData.realvalue+
                            ". You must validate your change by enter key.'><i class='fa fa-recycle'></i></span>";
                    ret +="<input id='" + id + "' name='CmdClssValue' class='form-control input-sm' type='number' aria-describedby='stch"+ valueRef + "' min='" +
                            valueData.min  +" ' max='"+ valueData.max  +"' value='"+ valueData.value +
                            "' data-toggle='tooltip' data-placement='bottom' title='range "+valueData.min+" to "+valueData.max+"'></input>" +
                            modify + "</div>";
                    break;
                case 'Raw' :
                case 'String' :
                    ret = renderInputText( id, "valueN", "value", valueData.value, "");
                    break;
                case 'Schedule' :
                    ret ="<input id='" + id + "' name='CmdClssValue' class='ccvalue' type='date' value='"+ valueData.value +
                         "' data-toggle='tooltip' data-placement='bottom' title=''></input>";
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
                    ret ="<button id='" + id + "' name='CmdClssValue' class='btn btn-default btn-xs' type='button' value='" + valueData.label +
                         "' data-toggle='tooltip' data-placement='bottom' title=''>"+ valueData.label +"</v>";
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
        return "<span id='hc"+valueRef +"'data-toggle='tooltip' data-placement='bottom' title='" + valueData.help +
               "'>" + valueData.commandClass + "</span>";
    } else {
        return "No data :(";
    };
};
