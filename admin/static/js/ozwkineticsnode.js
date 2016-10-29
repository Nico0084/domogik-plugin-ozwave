// Neighboors and group association library for showing zwave node device.
var grpsStage;
var neighborsGraph;
var MINFORCE = 10;

var nodeStateColor = {'inCarou' : [0, "#E9FBAA", 1, "#DCD100"],         // yellow
                      'inCarouSelect': [0, "#685CDA", 1, "#1200B5"], // blue
                      'inGrp': [0, "#FFA9FF", 1, "#DC00D9"],              // pink
                      'inGrpSelect': [0, "#FC9090", 1, "#D00000"]     // red
                     };

function getMinForce() {
    if (nodesData.length > 10) {
        return MINFORCE * nodesData.length;
    } else {
        return MINFORCE * 10;
    };
};

KtcNode = function  (x, y, r, nodeZW, layer, graph) {
    this.nodeZW = nodeZW;
    this.ktcGraph = graph;
    this.pictureNode = new Kinetic.Group({
        x: x,
        y: y,
        draggable: true,
        name: 'picturenode',
        ktcNode : this,
        dragBoundFunc : function(pos){
            var newPos = {x: pos.x, y: pos.y};
            if (dragConstrain && this.attrs.ktcNode.nodeZW.Capabilities.indexOf("Primary Controller" ) == -1) {
                var scale = this.attrs.ktcNode.ktcGraph.nodeLayer.scale();
                var offset = this.attrs.ktcNode.ktcGraph.nodeLayer.offset();
                var scalePos = {x:(pos.x+offset.x)/scale.x , y:(pos.y+offset.y)/scale.y};

                var radius = getMinForce() + getGraphForce(this.attrs.ktcNode.nodeZW);
                var ktcCtrl = GetControllerNode(this.attrs.ktcNode.nodeZW.NetworkID).ktcNode;
                if (ktcCtrl) {
                    var center = ktcCtrl.position() // center point
                } else {
                    var center = {x: this.attrs.ktcNode.ktcStage.getWidth() / 2,
                                  y: this.attrs.ktcNode.ktcStage.getHeight() / 2};
                };
                var ratio = Math.sqrt(Math.pow(scalePos.x - center.x, 2) + Math.pow(scalePos.y - center.y, 2)) / radius ; // distance formula ratio
                if (ratio < 0.8 || ratio > 1.2) {
                    var a = (scalePos.y - center.y)/(scalePos.x - center.x);
                    var b = center.y- (a * center.x);
                    var t = ratio < 0.8 ? 0.8 : 1.2;
                    var len = radius * t;
                    if (scalePos.x < center.x) { len = -len;};
                    var x = center.x;
                    var y = center.y;
                    scalePos = getPointTension(x, y, a, b, len);
                    newPos = {x:(scalePos.x*scale.x)-offset.x, y:(scalePos.y*scale.y)-offset.y};
                };
            };
            return newPos;
        }
    });
    var op =1;
    var label = getLabelDevice(this.nodeZW);
    if (this.nodeZW['State sleeping']) {op = 0.3; };
    if (this.nodeZW.DmgProducts.length != 0 && this.nodeZW.DmgProducts[0].picture != undefined) { // Display image  product instead of circle
        var imgP = new Image();
        this.pictProd = imgP;
        var kNode = this;
        var that = this;
        var imgSize = r * 1.3;
        this.pictProd.onload = function(){
            var img = new Kinetic.Image({
                x: -imgSize,
                y: -imgSize,
                image: imgP,
                width: 2*imgSize,
                height: 2*imgSize,
                name:"pictProd",
                ktcNode : kNode
              });
            that.pictureNode.add(img);
            img.moveToBottom();
            img.attrs.ktcNode.updateLinkPath();
        };
        this.pictProd.src = '/rest/product/'+clientID+'/'+this.nodeZW.DmgProducts[0].picture;
        var yT = r+5;
        var xT = -(label.length *3.2);
        if (label.length > ((2*imgSize)/5)) {
            xT = -imgSize;
        };
        var widthT = -2*xT;
        this.pictureImg = new Kinetic.Rect({
            x: xT,
            y: r,
            width: widthT,
            height: 20,
            cornerRadius: 8,
            fillLinearGradientStartPoint: {x:5, y:20},
            fillLinearGradientEndPoint: {x:widthT/2, y:0},
            fillLinearGradientColorStops: this.getColorState(),
            stroke: 'black',
            strokeWidth: 2,
            shadowColor: 'black',
            shadowBlur: 2,
            shadowOffset: {x:5,y:5},
            shadowOpacity: 0.5,
            name:"pictureImg",
            opacity: op,
            ktcNode : this
        });
    } else {
        this.pictureImg = new Kinetic.Circle({
            x: 0,
            y: 0,
            radius: r,
            fillRadialGradientStartPoint: 0,
            fillRadialGradientStartRadius: 0,
            fillRadialGradientEndPoint: 0,
            fillRadialGradientEndRadius: r,
            fillRadialGradientColorStops: this.getColorState(),
            stroke: 'black',
            strokeWidth: 2,
            shadowColor: 'black',
            shadowBlur: 2,
            shadowOffset: {x:5,y:5},
            shadowOpacity: 0.5,
            name:"pictureImg",
            opacity: op,
            ktcNode : this
        });
        var xT = -r +2;
        var widthT = 2*r-4;
        if (label.length > ((2*r)/5)) { yT = 8-r;
        } else {yT = -5;};
    };
    this.text = new Kinetic.Text({
        x: xT,
        y: yT,
        width: widthT,
        text: label,
        fontSize: 12,
        fontFamily: "Calibri",
        fill: "black",
        align : "center"
    });
    var s = this.text.size();
    if (this.pictureImg.className == "Rect"){
        this.pictureImg.height(s.height+10);
    };
    this.pictureNode.add(this.pictureImg);
    this.pictureNode.add(this.text);
    this.links = new Array ();
    this.layer = layer;

    this.pictureNode.on("mouseover touchstart", function() {
        var img = this.get(".pictureImg");
        img[0].setFillRadialGradientColorStops([0, 'turquoise', 1, 'blue']);
        img[0].opacity(0.5);
        var layerL;
        for (var idx in this.attrs.ktcNode.links) {
            this.attrs.ktcNode.links[idx].link.opacity(1);
            layerL = this.attrs.ktcNode.links[idx].layer;
        };
        if (layerL != undefined) { layerL.draw();};
        this.parent.draw();
        document.body.style.cursor = "pointer";
        setupContextMenuNode(this);
        });

    this.pictureNode.on("mouseout touchend", function() {
        var img = this.get(".pictureImg");
        img[0].setFillRadialGradientColorStops(this.attrs.ktcNode.getColorState());
        this.attrs.ktcNode.ktcGraph.tooltip.hide();
        var op =1;
        if (this.attrs.ktcNode.nodeZW['State sleeping']) {op = 0.3; };
        img[0].opacity(op);
        var layerL;
        for (var idx in this.attrs.ktcNode.links) {
            this.attrs.ktcNode.links[idx].link.opacity(0.5);
            layerL = this.attrs.ktcNode.links[idx].layer;
        };
        if (layerL != undefined) { layerL.draw();};
        this.parent.draw();
        this.attrs.ktcNode.ktcGraph.tooltipLayer.draw();
        document.body.style.cursor = "default";
    });

    this.pictureNode.on("dragstart", function() {
        if (this.attrs.ktcNode.nodeZW.Capabilities.indexOf("Primary Controller" ) == -1 ) {
            this.dragHelper = new Kinetic.Group({
                x: 0,
                y: 0,
                draggable: false,
                name: 'dragHelper'
            });
            var ray = getMinForce() + getGraphForce(this.attrs.ktcNode.nodeZW);
            var ktcCtrl = GetControllerNode(this.attrs.ktcNode.nodeZW.NetworkID).ktcNode;
            if (ktcCtrl) {
                var org = ktcCtrl.position(); // center point
            } else {
                var org = {x: this.attrs.ktcNode.ktcStage.getWidth() / 2,
                           y: this.attrs.ktcNode.ktcStage.getHeight() / 2};
            };
            var size = this.attrs.ktcNode.size();
            var s = Math.sqrt(Math.pow(size.width, 2) + Math.pow(size.height, 2))/2;
            this.dragHelper.add(new Kinetic.Circle({
                x: org.x,
                y: org.y,
                radius: (0.9 * ray) - s,
                stroke: 'black',
                strokeWidth: 2,
                dash: [10, 5],
                name:"DragCircle"
                })
            );
            this.dragHelper.add(new Kinetic.Circle({
                x: org.x,
                y: org.y,
                radius: (1.1 * ray) + s,
                stroke: 'red',
                strokeWidth: 2,
                dash: [10, 5],
                name:"DragCircle"
            })
            );
            this.parent.add(this.dragHelper);
        };
        this.attrs.ktcNode.ktcGraph.tooltip.hide();
        this.attrs.ktcNode.ktcGraph.tooltipLayer.draw();
        this.moveToTop();
    });

    this.pictureNode.on("dragend", function() {
        if (this.dragHelper != undefined) {
            this.dragHelper.destroyChildren();
            this.dragHelper.destroy();
        };
    });

    this.pictureNode.on("dragmove", function() {
        this.attrs.ktcNode.updateLinkPath();
    });

    this.pictureNode.on("mousemove", function(){
        var mousePos = this.attrs.ktcNode.ktcGraph.ktcStage.getPointerPosition();
        this.attrs.ktcNode.ktcGraph.tooltip.x(mousePos.x)
        this.attrs.ktcNode.ktcGraph.tooltip.y(mousePos.y - 5);
        var t = this.attrs.ktcNode.nodeZW.Type + ', Quality : ' + this.attrs.ktcNode.nodeZW.ComQuality + '%';
        for (var i=0; i<this.attrs.ktcNode.nodeZW.Groups.length; i++) {
            if (this.attrs.ktcNode.nodeZW.Groups[i].members.length !==0) {
                t = t+ '\n associate with node : ';
                for (var ii=0; ii<this.attrs.ktcNode.nodeZW.Groups[i].members.length; ii++) {
                    t += this.attrs.ktcNode.nodeZW.Groups[i].members[ii].node;
                    if (this.attrs.ktcNode.nodeZW.Groups[i].members[ii].instance != 0) {
                        t += '(' + this.attrs.ktcNode.nodeZW.Groups[i].members[ii].instance + ')';
                    };
                    t += ', ';
                };
            } else {
             t = t+ '\n no association ';
            };
            t = t + ' in index ' + this.attrs.ktcNode.nodeZW.Groups[i].index + ' named :' + this.attrs.ktcNode.nodeZW.Groups[i].label;
        };
        this.attrs.ktcNode.ktcGraph.tooltip.getText().text(t);
        this.attrs.ktcNode.ktcGraph.tooltip.show();
        this.attrs.ktcNode.ktcGraph.tooltipLayer.draw();
        mousePos=0;
    });
    this.layer.add(this.pictureNode);
};

KtcNode.prototype.destroy = function () {
    for (var idx in this.links) {
            this.links[idx].destroy();
    };
    this.pictureNode.destroy();
    this.layer.draw();
};

KtcNode.prototype.haslinktonode = function(nodeZW) {
    if (this.nodeZW.Neighbors.indexOf(nodeZW.NodeID) != -1) {
        return true;
    };
    return false;
};

KtcNode.prototype.getLinkToNode = function(ktcNode) {
    for (var idx in this.links) {
        if (ktcNode.nodeZW.NodeID == this.links[idx].ktcNodes[1].nodeZW.NodeID) {
                return this.links[idx];
            };
    };
    return false;
};

KtcNode.prototype.addlink = function(linker) {
    var idx = this.links.indexOf(linker);
    if (idx == -1) {
        this.links.push(linker);
    };
};

KtcNode.prototype.removelink= function(linker) {
    var idx = this.links.indexOf(linker);
    if (idx == -1) {
        this.links[idx].destroy();
        this.links.splice(idx, 1);
        linker.draw();
    };
};

KtcNode.prototype.checklinks = function() {
    var id, id2;
    for (var idx in this.links) {
        var id = this.links[idx].ktcNodes.indexOf(this);
        id2 = (id ==0) ? 1 : 0;
        if (this.nodeZW.Neighbors.indexOf(this.links[idx].ktcNodes[id2].nodeZW.NodeID) == -1) {
            if (this.links[idx].ktcNodes[id2].nodeZW.Neighbors.indexOf(this.nodeZW.NodeID) == -1) {
            // Link must me removed
                this.links[idx].destroy();
                this.links.splice(idx, 1);
            };
        };
    };
    var create = true;
    if (typeof this.nodeZW.Neighbors != "string") {
        for (var in1=0; in1<this.nodeZW.Neighbors.length; in1++) {
            nodeData2 = GetZWNode(this.nodeZW.NetworkID, this.nodeZW.Neighbors[in1]);
            if (nodeData2 && nodeData2.ktcNode != undefined) {
                var link = this.getLinkToNode(nodeData2.ktcNode);
                if (!link) {
                    link = new KtcLink(this, nodeData2.ktcNode, this.ktcGraph.linkLayer);
                    this.addlink(link);
                };
                nodeData2.ktcNode.addlink(link);
                link = nodeData2.ktcNode.getLinkToNode(this);
                if (!link) {
                    link = new KtcLink(nodeData2.ktcNode, this, this.ktcGraph.linkLayer);
                    nodeData2.ktcNode.addlink(link);
                };
                this.addlink(link);
            };
        };
    };
    this.ktcGraph.linkLayer.draw();
};

KtcNode.prototype.getColorState = function() {
    var colors = [0, 'yellow', 0.5, 'orange', 1, 'blue'];
    switch (this.nodeZW['InitState']) {
        case 'Uninitialized' :
            colors = [0, 'red', 0.5, 'orange', 1, 'red'];
            break;
        case 'Initialized - not known' :
            colors = [0, 'orange', 0.5, 'orange', 1, 'yellow'];
            break;
        case 'Completed' :
            colors = [0, 'yellow', 0.5, 'yellow', 1, 'green'];
            break;
        case 'In progress - Devices initializing' :
            colors = [0.2, 'yellow', 0.6, 'green', 1, 'orange'];
            break;
        case 'In progress - Linked to controller' :
            colors = [0, 'brown', 0.5, 'violet', 1, 'turquoise'];
            break;
        case 'In progress - Can receive messages' :
            colors = [0, 'violet', 0.5, 'turquoise', 1, 'blue'];
            break;
        case 'Out of operation' :
            colors = [0, 'red', 0.5, 'red', 1, 'orange'];
            break;
        case 'In progress - Can receive messages (Not linked)' :
            colors = [0, 'turquoise', 0.7, 'yellow', 1, 'red'];
            break;
        };
    return colors;
    };

KtcNode.prototype.getTypeLink = function() {
    var indice = 1, color = 'green';
    if (this.nodeZW.Capabilities.indexOf("Routing") != -1) {indice = indice + 2; color ='#64FE2E';} // green light
    if (this.nodeZW.Capabilities.indexOf("Beaming" ) != -1) {indice = indice + 1;}
    if (this.nodeZW.Capabilities.indexOf("Listening" ) != -1) { indice = indice + 2; color ='#2E64FE';} // blue light
    if (this.nodeZW.Capabilities.indexOf("Security") != -1) { color ='yellow';}
    if (this.nodeZW.Capabilities.indexOf("FLiRS") != -1) { indice = indice + 2;}
    if (this.nodeZW.Capabilities.indexOf("Primary Controller" ) != -1 ) { indice += 5;  color ='blue';}
    if (this.nodeZW['State sleeping']) {indice = indice -2; color = 'orange';}
    if (indice < 1) {indice =1;};
    if (this.nodeZW['InitState'] == 'Out of operation') {indice = 1,  color = 'red';}
    return {'indice' : indice, 'color' : color}
};

KtcNode.prototype.update = function() {
    this.checklinks();
    this.ktcGraph.tooltip.hide();
    var op =1;
    if (this.nodeZW['State sleeping']) {op = 0.3; };
    if (this.pictureImg.className == "Rect"){
        this.pictureImg.setFillLinearGradientColorStops(this.getColorState());
    } else {
        this.pictureImg.setFillRadialGradientColorStops(this.getColorState());
    };
    this.pictureImg.opacity(op);
    for (var l in this.links)  {this.links[l].update();};
    this.ktcGraph.linkLayer.batchDraw ();
    this.ktcGraph.tooltipLayer.batchDraw ();
    this.layer.batchDraw ();
//    console.log('redraw kinetic node :' + this.nodeZW.NodeID);
};

KtcNode.prototype.updateLinkPath = function() {
    var layer;
    var qPts;
    for (var i=0; i< this.links.length;i++) {
        if (this.links[i].calculatePos) {
            var qPts = this.links[i].ktcNodes[0].ktcGraph.findPath(
                    this.links[i].ktcNodes[0],
                    this.links[i].ktcNodes[1]);
            this.links[i].link.attrs.curved =  qPts.curved;
            this.links[i].calculatePos = false;
            layer = this.links[i].follownode(this, qPts);
        };
    };
    if (layer != undefined) {layer.batchDraw();};
};

KtcNode.prototype.position = function() {
    if (this.pictureImg.className == "Rect"){
        var scale = this.ktcGraph.nodeLayer.scale();
        var offset = this.ktcGraph.nodeLayer.offset();
        var img = this.pictureNode.get(".pictProd");
        var sRect = this.pictureImg.size();
        var pRect = this.pictureImg.getAbsolutePosition();
        var xm,ym;
        if (img.length > 0 ) {
            var x,y,x1,y1;
            var pImg = img[0].getAbsolutePosition();
            if (pImg.x < pRect.x) {x = pImg.x;} else { x = pRect.x;};
            if (pImg.x+img[0].size().width < pRect.x+sRect.width) {x1 = pImg.x+img[0].size().width;} else { x1 = pRect.x+sRect.width;};
            y = pImg.y;
            y1 = pRect.y + sRect.height;
            xm = (x1 - x)/2 + x;
            ym = (y1 - y)/2 + y;
        } else {
            xm = pRect.x+(sRect.width/2);
            ym = pRect.y+(sRect.height/2);
        };
        return {x:(xm + offset.x)/scale.x, y:(ym + offset.y)/scale.y};
    };
    return this.pictureNode.position();
};

KtcNode.prototype.size = function() {
    if (this.pictureImg.className == "Rect"){
        var img = this.pictureNode.get(".pictProd");
        var size = this.pictureImg.size();
        if (img.length > 0 ) {
            size.height += img[0].size().height;
            size.width += img[0].size().width;
        };
        return size;
    };
    return this.pictureImg.size();
};

// Groups associations functions

// Basic Kinetics objet for group association

KtcNodeGrp = function  (x, y, r, node, instanceAssoc, layer, grpAssociation) {
    this.nodeObj = node;
    this.instanceAssoc = instanceAssoc;
    this.pictNodeGrp = new Kinetic.Group({
          x: x,
          y: y,
          draggable: true,
          name : "nodegrp",
          nodeP : this
        });
    var textI = "";
    if (typeof(grpAssociation)=='undefined'){
        this.grpAss = layer;
        f = nodeStateColor.inCarou; //'yellow';
    } else {
        this.grpAss = grpAssociation;
        f = nodeStateColor.inGrp; //'pink';
        textI = this.getTextInstance();
    };
    this.pictureImg = new Kinetic.Circle({
        x: 0,
        y: 0,
        radius: r,
        fillRadialGradientStartPoint: {x:0,y:0},
        fillRadialGradientStartRadius: 0,
        fillRadialGradientEndPoint: {x:0,y:0},
        fillRadialGradientEndRadius: r,
        fillRadialGradientColorStops: f,
        stroke: 'black',
        strokeWidth: 2,
        shadowColor: 'black',
        shadowBlur: 5,
        shadowOffset: {x:5,y:2},
        shadowOpacity: 0.7,
        name:"pictureImg"
        });
    this.text = new Kinetic.Text({
        x: -r + 2,
        y: -r + 2 + 8,
        width: 2*r-4,
        text: "" + node.NodeID,
        fontSize: 16,
        fontFamily: "Calibri",
        fill: "black",
        align : "center"
    });
    this.textInstance = new Kinetic.Text({
        x: -5,
        y: r - 10,
        width: r,
        text: textI,
        fontSize: 12,
        fontFamily: "Calibri",
        fill: "white",
        align : "right"
    });
    this.tooltip = new Kinetic.Label({
        x: 0, // x,
        y: -r, // y-r,
        draggable: false
    });
    this.tooltip.add(new Kinetic.Tag({
        fill: '#81DAF5',
        stroke: '#333',
        shadowColor: 'black',
        shadowBlur: 10,
        shadowOffset: {x:8,y:8},
        shadowOpacity: 0.5,
        lineJoin: 'round',
        pointerDirection: 'down',
        pointerWidth: 10,
        pointerHeight: 20,
        cornerRadius: 10
    }));
    this.tooltip.add(new Kinetic.Text({
        text: "" + node.Type,
        fontSize: 12,
        fontFamily: "Calibri",
        fill: "black",
        align : "left",
        padding: 3
    }));
    var imgstate = new Image();
    this.imgstate = imgstate;
    this.state = 'unknown';
    this.pictNodeGrp.add(this.pictureImg);
    this.pictNodeGrp.add(this.text);
    this.pictNodeGrp.add(this.textInstance);
    this.pictNodeGrp.add(this.tooltip);
    var grp = this.pictNodeGrp;
    this.imgstate.onload = function() {
        if (!this.init) {var st = new Kinetic.Image({
            x: -r-12,
            y: -r-12,
            image: imgstate,
            width: 24,
            height: 24,
            name: 'stateImg',
            visible: false
        });
        this.init = true;
        grp.add(st);
        grp.attrs.nodeP.kImg = st;
        };
    };
    this.imgstate.src =  '/plugin_ozwave/static/images/status/check_32.png'; // pour l'init
    this.xOrg = x;
    this.yOrg = y;
    this.rOrg = r;
    this.layer = layer;
    this.state = 'unknown';
    this.moveInGrp = undefined;
    var self = this;
    setTimeout(function () {
            if (self.grpAss == grpAssociation) {
            for (var i = 0; i<self.grpAss.grpAss.members.length; i++){
                 if (self.nodeObj.NodeID == self.grpAss.grpAss.members[i].node){
                    self.setimgstate(self.grpAss.grpAss.members[i].status);
                    break;
                 };
             };
             self.layer.draw();
         };}, 300, self , grpAssociation);

    this.pictNodeGrp.on("mouseenter touchstart", function(e) {
        var img = this.get(".pictureImg");
        var color = nodeStateColor.inCarouSelect;
        if (this.attrs.nodeP.isMember()) {color = nodeStateColor.inGrpSelect};
        img[0].fillRadialGradientColorStops(color);
        img[0].opacity(0.5);
        var t ='';
        if (this.attrs.nodeP.nodeObj.Name != "Undefined" && this.attrs.nodeP.nodeObj.Name !="") {
            t = this.attrs.nodeP.nodeObj.Name;
        } else {
            t = this.attrs.nodeP.nodeObj.Model.replace(" -- ","\n");
        };
        t += '\n' + this.attrs.nodeP.nodeObj.Type;
        this.attrs.nodeP.tooltip.getText().text(t);
        this.attrs.nodeP.tooltip.show();
        this.parent.draw();
        document.body.style.cursor = "pointer";
    });

    this.pictNodeGrp.on("mouseleave touchend", function(e) {
        var img = this.get(".pictureImg");
        if (img.length != 0) { // le node detruit genère quand même un mouseout après sa destruction
            var color = nodeStateColor.inCarou;
            if (this.attrs.nodeP.isMember()) {color = nodeStateColor.inGrp};
            img[0].fillRadialGradientColorStops(color);
            img[0].opacity(1);
            this.attrs.nodeP.tooltip.hide();
            this.parent.draw();
            document.body.style.cursor = "default";
        } else {
            console.log("Persistance node remove");};
        this.getStage().draw();
    });

    this.pictNodeGrp.on("dragstart", function(e) {
//        console.log("dragstart node :" + this.attrs.nodeP.nodeObj.NodeID);
        var newstate = 'unallowable';
        if (!this.attrs.nodeP.isMember()) {
            this.attrs.nodeP.duplicateIt()
            this.attrs.nodeP.setState(newstate);
        };
        if (this.attrs.nodeP.grpAss.layer) {this.parent.moveToTop();
        } else {this.moveToTop();}
    });

    this.pictNodeGrp.on("dragmove", function(e) {
        var inGrp = this.attrs.nodeP.inGroup();
        if (!this.attrs.nodeP.isMember()) {
            if (this.moveInGrp != undefined) {this.moveInGrp.attrs.grpAssP.fondImg.stroke('black');};
            if (inGrp){
                this.scale({x:0.8,y:0.8});
                this.attrs.nodeP.setState('add', inGrp.attrs.grpAssP);
                inGrp.attrs.grpAssP.fondImg.stroke('red');
                this.moveInGrp = inGrp;
            } else {
                this.scale({x:1,y:1});
                this.attrs.nodeP.setState('unallowable');
                if (this.moveInGrp != undefined) {
                    this.moveInGrp.attrs.grpAssP.fondImg.stroke('black');
                    this.moveInGrp = undefined;
                    };
            };
        } else {
             if (inGrp && inGrp.attrs.grpAssP == this.attrs.nodeP.grpAss){
                var isAMember = inGrp.attrs.grpAssP.isAMember(this.attrs.nodeP.nodeObj, inGrp.attrs.grpAssP.nodeOwner.MultiInstanceAssoc, this.attrs.nodeP.instanceAssoc);
                if (isAMember) {
                    this.attrs.nodeP.setState(isAMember.status, inGrp.attrs.grpAssP);
                } else {
                    this.attrs.nodeP.setState('to update', inGrp.attrs.grpAssP);
                };
            } else {
                this.attrs.nodeP.setState('del');
            };
        };
        this.getStage().draw();
    });

    this.pictNodeGrp.on("dragend", function(e) {
//        console.log("dragend node :" + this.attrs.nodeP.nodeObj.NodeID);
        var inGrp = this.attrs.nodeP.inGroup();
        this.attrs.nodeP.tooltip.hide();
        if (!this.attrs.nodeP.isMember()) {
            if (!inGrp){
                this.removeChildren();
//                console.log("Hors d'un groupe, destruction de la copie.");
                delete(this.attrs.nodeP);
                delete(this);
            }else {
//                console.log('dans un groupe, ajouter au groupe si pas doublon.');
                if (!inGrp.attrs.grpAssP.isAMember(this.attrs.nodeP.nodeObj, inGrp.attrs.grpAssP.nodeOwner.MultiInstanceAssoc, this.attrs.nodeP.instanceAssoc)) {
                    addInGrpAssoc(inGrp.attrs.grpAssP, this.attrs.nodeP)
                } else {
//                    console.log('En doublons, suppression de la copie');
                    this.removeChildren();
                    delete(this.attrs.nodeP);
                    delete(this);
                    inGrp.attrs.grpAssP.fondImg.stroke('black');
                };
            };
        } else {
            if ((inGrp==null) || (inGrp.attrs.grpAssP != this.attrs.nodeP.grpAss)){
                this.attrs.nodeP.grpAss.delNode(this.attrs.nodeP);
                this.removeChildren();
//                console.log('Hors du groupe, node retiré du group et détruit');
            }else {
//                console.log('toujours dans le groupe, remis à sa place.');
                this.x(this.attrs.nodeP.xOrg).y(this.attrs.nodeP.yOrg);
                };
            };
        this.getStage().draw();
    });

    this.pictNodeGrp.on("mousedown", function(e) {
        this.moveToTop();
    });

    this.layer.add(this.pictNodeGrp);
    this.tooltip.hide();
};

KtcNodeGrp.prototype.isMember = function() {
    if (this.grpAss == this.layer) { return null;
    } else { return this.grpAss;};
};

KtcNodeGrp.prototype.inGroup = function() {
    var stage = this.pictNodeGrp.getStage();
    var groups = stage.get('.ngroupass');
    var retval = null, isSelf=-1;
    var pos = this.pictNodeGrp.getAbsolutePosition();
    var gPos, gSize;
        for (var i=0; i< groups.length; i++) {
            var gPos = groups[i].getAbsolutePosition();
            var gSize = groups[i].getSize();
            if (pos.x >= gPos.x && pos.x <= gPos.x + gSize.width && pos.y >= gPos.y && pos.y <= gPos.y + gSize.height) {
                retval = groups[i];
                break;
            };
        };
    return retval;
};

KtcNodeGrp.prototype.duplicateIt = function() {
    var stage = this.pictNodeGrp.getStage();
    var n = new KtcNodeGrp(this.xOrg, this.yOrg, this.rOrg, this.nodeObj, this.instanceAssoc, stage.elemsLayer);
    stage.draw();
};

KtcNodeGrp.prototype.getTextInstance = function() {
    var textI = "";
    for (var i = 0; i<this.grpAss.grpAss.members.length; i++){
        if (this.nodeObj.NodeID == this.grpAss.grpAss.members[i].node && this.instanceAssoc == this.grpAss.grpAss.members[i].instance){
            stOrg  = true;
            if (this.grpAss.grpAss.members[i].instance != 0) {
                textI = ""+this.grpAss.grpAss.members[i].instance;
            };
            break;
        };
    };
    return textI;
};

KtcNodeGrp.prototype.setimgstate = function(state) {
    if (this.state != state) {
        this.state = state;
        switch (state) {
            case mbrGrpSt[0] : // 'unknown'
                this.imgstate.src =  '/plugin_ozwave/static/images/status/unknown_red_32.png';
                if (this.kImg) {this.kImg.show();};
                break;
            case mbrGrpSt[1] : // 'confirmed'
                this.imgstate.src = '/plugin_ozwave/static/images/status/check_32.png';
                if (this.kImg) {
                    if (this.pictNodeGrp.scale().x == 0.8) {
                        this.kImg.show();
                    } else {
                        this.kImg.hide();
                    };
               };
                break;
            case mbrGrpSt[2] : //'to confirm'
                this.imgstate.src =  '/plugin_ozwave/static/images/status/unknown_green_32.png';
                if (this.kImg) {this.kImg.show();};
                break;
            case mbrGrpSt[3] : //'to update'
                this.imgstate.src =  '/plugin_ozwave/static/images/action/refresh_16.png';
                if (this.kImg) {this.kImg.show();};
                break;
            case 'add':
                this.imgstate.src =  '/plugin_ozwave/static/images/action/plus_32.png';
                if (this.kImg) {this.kImg.show();};
                break;
            case 'del':
                this.imgstate.src = '/plugin_ozwave/static/images/action/minus_32.png';
                if (this.kImg) {this.kImg.show();};
                break;
             case 'unallowable':
                this.imgstate.src =  '/plugin_ozwave/static/images/status/wrong_32.png';
               if (this.kImg) { this.kImg.show();};
                break;
        };
        this.layer.draw();
    };
};

KtcNodeGrp.prototype.setState = function(state, inGrpAss) {
    var img = this.kImg;
    if (img) { // le node detruit genère quand même un move event après sa destruction;
         var isMember = (this.grpAss != this.layer);
         if (isMember) {
            this.textInstance.text(this.getTextInstance());
         };
         var isAMember = null;
         if (inGrpAss) {
             isAMember = inGrpAss.isAMember(this.nodeObj, inGrpAss.nodeOwner.MultiInstanceAssoc, 0); // TODO: Gérer l'instance
        };
         switch (state) {
            case 'add':
                if (isAMember || (inGrpAss.members.length >= inGrpAss.grpAss.maxAssociations)) {
                    this.setimgstate('unallowable');
                }else {this.setimgstate('add');};
                break;
            case 'del':
            case 'unallowable':
            case 'to update':
                this.setimgstate(state);
                break;
            default:
                this.setimgstate(state);
        };
    };
};

KtcGrpAss = function (x,y,w, maxLi, nodeData, grp,stage) {
    this.nodeOwner = nodeData;
    var nbCol = 4, hHead = 50, r = 16;
    this.nbLi = Math.ceil(grp.maxAssociations / nbCol);
    if (this.nbLi > maxLi) {this.dispLi = maxLi; var scrolled = true;  var sColor = "#90C633";
    } else { this.dispLi = this.nbLi; var scrolled = false;  var sColor = "#669966";};
    this.LiStep = 2*r +10;
    var h= hHead + (this.dispLi * this.LiStep) + 10;
    w = 10+ (nbCol * this.LiStep) + 10;
    this.tabN=[];
    for (var i=0; i < this.nbLi; i++){
        for (var ii=0; ii< nbCol;ii++){
            this.tabN.push({x: 5+ (ii * this.LiStep) + r, y: (i * this.LiStep) + r  + 5, kN: null});
        };
    };
    this.picture = new Kinetic.Group({
        x: x,
        y: y,
        width: w,
        height: h,
        draggable: false,
        name : "ngroupass",
        grpAssP : this,
        });
    this.fondImg = new Kinetic.Rect({
        x: 0,
        y: 0,
        width: w,
        height: h,
        fillLinearGradientStartPoint: {x:0, y:0},
        fillLinearGradientEndPoint: {x:0, y:h},
        fillLinearGradientColorStops: [0, '#BDCB2F', 1, '#D3F0A1'],
        shadowColor: 'black',
        shadowBlur: 8,
        shadowOffset: {x:5,y:5},
        shadowOpacity: 0.7,
        stroke: 'black',
        strokeWidth: 3,
        name:"fondGrp"
        });
    this.infos = new Kinetic.Label({
        x: 3,
        y: 3,
        draggable: false
    });
    this.infos.add(new Kinetic.Text({
        height: w,
        text: "", // "Group " + grp.index + ", " + grp.label + "\n Max members* : "+grp.maxAssociations + "\n Members : " + strmembers,
        fontSize: 12,
        fontFamily: "Calibri",
        fill: "black",
        align : "left"
    }));

    this.nodeArea = new Kinetic.Group({
        x: x,
        y: y+hHead,
        width: w,
        height: h - hHead,
        draggable: false,
        name : "nodeArea" + grp.index,
        clipFunc: function(canvas) {
            var context = canvas.getContext();
            context.rect(5, 0, w-10, h - hHead-5);
        }
    });

 // vertical scrollbars
    var wsc = 10;
    this.vscrollArea = new Kinetic.Rect({
        x: w - wsc,
        y: hHead,
        width: wsc,
        height: h - hHead,
        fill: "black",
        opacity: 0.3,
        name: 'scrollarea'+ grp.index
    });
    var hs = (h - hHead) / (this.nbLi - this.dispLi + 1);
    this.vscroll = new Kinetic.Rect({
        x: w - wsc,
        y: hHead,
        width: wsc,
        height: hs,
        fill: sColor,
        draggable: true,
        clearBeforeDraw: true,
        dragBoundFunc: function(pos) { // vertical
            var yA = this.area.getAbsolutePosition().y;
            var newY = yA;
            var h = this.area.height();
            var hs = this.height();
            if ((pos.y > yA) && ( pos.y <= h + yA - hs)) {
                newY = pos.y;
            } else if (pos.y >  h + yA - hs) {
                newY =  h+yA - hs;
            };
            var offset = this.nodeArea.getOffset();
            var stepS = h / (this.parent.grpAss.nbLi - this.parent.grpAss.dispLi + 1);
            var ratio = (newY - yA) / stepS;
            var yOffset = this.parent.grpAss.LiStep * ratio ;
            this.nodeArea.offsetY(yOffset);
            this.nodeArea.getParent().draw();
            return {
                x: this.getAbsolutePosition().x,
                y: newY
            };
        },
        opacity: 0.9,
        stroke: "black",
        strokeWidth: 1,
        name: 'scrollbar'+ grp.index
    });
    this.vscroll.area = this.vscrollArea;
    this.vscroll.vscrollArea = this.vscrollArea;
    this.vscroll.nodeArea = this.nodeArea;

 // scrollbars events assignation
    if (scrolled) {
        this.vscroll.on("mouseover touchstart", function() {
            document.body.style.cursor = "pointer";
        });
        this.vscroll.on("mouseout touchend", function() {
            document.body.style.cursor = "default";
        });
        this.vscroll.on("dragstart", function() {
            this.parent.grpAss.showAll();
        });

        this.vscroll.on("dragend", function() {
            document.body.style.cursor = "default";
            this.parent.grpAss.clipArea();
        });
    } else {
        this.vscroll.hide();
        this.vscrollArea.hide();
    };
    this.scrollbar = new Kinetic.Group();
    this.scrollbar.grpAss = this;
    this.scrollbar.add(this.vscrollArea);
    this.scrollbar.add(this.vscroll);
    this.grpAss = grp;
    this.layer = stage.grpsLayer;
    this.picture.add(this.fondImg);
    this.picture.add(this.infos);
    this.picture.add(this.scrollbar);
    this.layer.add(this.picture);
    this.layer.add(this.nodeArea);
    this.members = [];
    var m;
    for (i=0; i < grp.members.length; i++){
        posm = getFreePosGrp(this.tabN);
        m = new KtcNodeGrp(this.tabN[posm].x, this.tabN[posm].y, r, GetZWNode(nodeData.NetworkID, grp.members[i].node), grp.members[i].instance, stage.grpsLayer,this);
        this.tabN[posm].kN = m;
        this.members.push(grp.members[i]);
        this.nodeArea.add(m.pictNodeGrp);
    };
    this.refreshText()
};

KtcGrpAss.prototype.clipArea = function() {
    var offset= this.nodeArea.getOffset().y;
    var size = this.nodeArea.getSize().height;
    var hHead = this.vscrollArea.getY();
    var r;
    var stepS = size / (this.nbLi - this.dispLi + 1);
    var step = Math.round(offset / this.LiStep);
    offset = step * this.LiStep;
    this.nodeArea.offsetY(offset);
    this.vscroll.y((step *  stepS) + hHead);
    for (i=0; i < this.tabN.length; i++){
        if (this.tabN[i].kN) {
            r = this.tabN[i].kN.pictureImg.attrs.radius;
            if (offset > this.tabN[i].y - r/2 || this.tabN[i].y + r > offset + size) {
                this.tabN[i].kN.pictNodeGrp.hide();
            } else {
                this.tabN[i].kN.pictNodeGrp.show();
            };
        };
    };
    this.layer.draw();
};

KtcGrpAss.prototype.showAll = function() {
    for (i=0; i < this.tabN.length; i++){
        if (this.tabN[i].kN) {this.tabN[i].kN.pictNodeGrp.show();};
        };
    this.layer.draw();
};

KtcGrpAss.prototype.refreshText = function (){
    var strmembers = '', sp='';
    for (var i in this.members) {
        strmembers += sp + this.members[i].node;
        if (this.members[i].instance != 0 ) {
            strmembers += '('+this.members[i].instance +')';
        };
        sp=', ';
    };
    this.infos.getText().text("Group " + this.grpAss.index + ", " + this.grpAss.label + "\n Max members : "+ this.grpAss.maxAssociations + "\n Members : " + strmembers);
    wrapText(this.infos.getText(), this.nodeArea.width())
    this.layer.draw();
};


KtcGrpAss.prototype.getDim = function (){
    var retval={};
    retval.pos=this.picture.getPosition();
    retval.size= this.picture.children[0].getSize();
    return retval;
};

KtcGrpAss.prototype.isAMember = function (nodeObj, multi, instance) {
    var retval = null;
    for (var i=0; i<this.members.length; i++) {
        if (this.members[i].node == nodeObj.NodeID && (!multi || this.members[i].instance == instance)) {
            retval = this.members[i];
            break;
        };
    };
    return retval
};

KtcGrpAss.prototype.addNode = function (kNode, instance) {
    if (!this.isAMember(kNode.nodeObj, this.nodeOwner.MultiInstanceAssoc, instance)) {
        if (this.members.length<this.grpAss.maxAssociations) {
            kNode.instanceAssoc = instance;
            this.members.push({node:kNode.nodeObj.NodeID, instance: instance, status: 'to update'});
            var posm = getFreePosGrp(this.tabN);
            if (posm!=-1) {
                this.tabN[posm].kN = kNode;
                kNode.pictNodeGrp.moveTo(this.picture);
                kNode.pictNodeGrp.x(this.tabN[posm].x).y(this.tabN[posm].y);
                kNode.xOrg = this.tabN[posm].x;
                kNode.yOrg = this.tabN[posm].y;
            this.refreshText();
            return true;
            } else {
//                console.log ("Plus de place disponible, pas d'ajout");
                return false};
        }else {
//            console.log ("Nombre max atteint, pas d'ajout");
            return false};
    } else { return false;};
};

KtcGrpAss.prototype.delNode = function (kNode) {
    var idx =-1;
    if (kNode.nodeObj) {
        for (var i =0; i< this.members.length; i++) {
            if (this.members[i].node == kNode.nodeObj.NodeID) {
                idx = i;
                break;
            };
        };
        if (idx != -1) {
            this.members.splice(idx, 1);
            for (var i=0; i<this.tabN.length;i++) {
                if (this.tabN[i].kN == kNode) {
                    this.tabN[i].kN = null;
                    break;
                };
            };
            this.refreshText();
            return true;
        } else { return false;};
    } else { //node ghost force delete it.
        for (var i=0; i<this.tabN.length;i++) {
            if (this.tabN[i].kN == kNode) {
                this.tabN[i].kN = null;
                break;
            };
        };
        for (var i =0; i< this.members.length; i++) { // check if node() exist and delete it from member list.
            if (GetZWNode(kNode.nodeObj.NetworkID, this.members[i].node) == false) {
                this.members.splice(i, 1);
            };
        };
        this.refreshText();
        return true;
    };
};

// Creating and build association groups stage
function createKineticsGrpAssoc(contName, nodeData) {
    var stage = buildStageGrps(contName);
    CreateGroups(stage, nodeData, contName);
    return stage;
};

// Create stage
function buildStageGrps(contName) {
    var width = 550, height= 470;
    $('#'+ contName).width(width).height(height);
    grpsStage = null;
    if (grpsStage) {
        grpsStage.reset();
        grpsStage.clear();
    } else {
          grpsStage = new Kinetic.Stage({
          container: contName,
          width: width,
          height: height
        });
    };
    grpsStage.tooltip = new Kinetic.Text({
        text: "essais",
        fontFamily: "Calibri",
        fontSize: 12,
        padding: 15,
        fill: "black",
        opacity: 1,
        visible: false
    });
    grpsStage.tooltipLayer = new Kinetic.Layer();
    grpsStage.tooltipLayer.add(grpsStage.tooltip);
    grpsStage.grpsLayer = new Kinetic.Layer();
    grpsStage.elemsLayer = new Kinetic.Layer();
    grpsStage.carouLayer = new Kinetic.Layer();
    grpsStage.add(grpsStage.grpsLayer);
    grpsStage.add(grpsStage.elemsLayer);
    grpsStage.add(grpsStage.carouLayer);
    grpsStage.add(grpsStage.tooltipLayer);
    return grpsStage;
};

KtcInitCarouselNodes = function (r, wArea, stage) {
    var hArea = 2*r;
    var maxSpeed = 60;
    var bgCoul = $(stage.attrs.container).css("background-color");
    var bgCoul = "#FFFFFF";
    var bord1 = new Kinetic.Rect({
        x: -11,
        y: 0,
        width: hArea,
        height: hArea + 10,
        fill: bgCoul,
        opacity: 1
    });
    var bord2 = new Kinetic.Rect({
        x: stage.width() - hArea + 11,
        y: 0,
        width: hArea,
        height: hArea + 10,
        fill: bgCoul,
        opacity: 1
    });
    this.wArea = wArea;
    this.layer = stage.carouLayer;
    this.layer.add(bord1);
    this.layer.add(bord2);
    this.imgGoLeft = new Image();
    var img = this.imgGoLeft;
    var layer = this.layer;
    var wSpace = stage.width() - bord1.width();
    this.imgGoLeft.onload = function () {
        var goL = new Kinetic.Image({
            x: 0,
            y: 7,
            image: img,
            width: 32,
            height: 32,
            name:  'left',
            visible: true,
            layer: layer,
            anim: new Kinetic.Animation(function(frame) {
                    var x = stage.elemsLayer.offsetX();
                    if (frame.timeDiff != 0) {x = x - ((frame.timeDiff * stage.carouLayer.speed)/100);};
                    if (x <= -wSpace) { x = wArea;};
                    stage.elemsLayer.offsetX(x);
                    if (stage.carouLayer.speed < maxSpeed) { stage.carouLayer.speed = stage.carouLayer.speed + (10 / (frame.frameRate+10)) ;};
                  }, stage.elemsLayer)
        });
        initGoAction(goL);
        layer.add(goL);
        layer.draw();
    };
    this.imgGoLeft.src =  '/plugin_ozwave/static/images/action/go_left_32.png';
    this.imgGoRight = new Image();
    var imgR = this.imgGoRight;
    this.imgGoRight.onload = function () {
        var goR = new Kinetic.Image({
            x: stage.width() - 32,
            y: 7,
            image: imgR,
            width: 32,
            height: 32,
            name:  'right',
            visible: true,
            layer: layer,
            anim: new Kinetic.Animation(function(frame) {
                    var x = stage.elemsLayer.offsetX();
                    if (frame.timeDiff != 0) {x = x + ((frame.timeDiff * stage.carouLayer.speed)/100);};
                    if (x >= wArea) {x= -wSpace;};
                    stage.elemsLayer.offsetX(x);
                    if (stage.carouLayer.speed < maxSpeed) { stage.carouLayer.speed=stage.carouLayer.speed+(10 / (frame.frameRate+10));};
                  }, stage.elemsLayer)
        });
        initGoAction(goR);
        layer.add(goR);
        layer.draw();
    };
    this.imgGoRight.src =  '/plugin_ozwave/static/images/action/go_right_32.png';
};


// Create windows groups for association groups
function CreateGroups(stage, nodeData, idDiv) {
    var wn = 40, hn = 40;
    var w = stage.width()-10;
    var h = stage.height()-10;
    var r =  Math.floor((wn-4) / 2);
    var wg = 200; //, hg = 250;
    var spw = 10, sph = 10;
    var nbcol=0, nbli=0;
    if (nodeData.Groups.length *(wg+spw) <w){
         nbcol= nodeData.Groups.length;
         nbli = 1;
    } else {
         nbcol = Math.floor(w / (wg+spw));
         nbli = Math.ceil(nodeData.Groups.length / nbcol);
    };
    var tabCol = calculateDimGrps(nbcol, nbli, nodeData.Groups, h-(2*r + 40));
    var ccol = -1, cli =0, x=0, y= 5;
    var imgGrp;
    var dimGrps = new Array();
    w = 0;
    h = 0;
    for (var gi=0; gi < nodeData.Groups.length; gi++) {
        if (ccol == nbcol-1) {
            ccol =0;
            y = dimGrps[ccol][cli].pos.y + dimGrps[ccol][cli].size.height + sph;
            cli++;
        } else {
            ccol++;
            if (cli == 0) {dimGrps[ccol] = new Array();
            } else {
                dimGrps[ccol].push({});
                y = dimGrps[ccol][cli-1].pos.y + dimGrps[ccol][cli-1].size.height + sph;
            };
        };
        x= (ccol * (wg+spw)) + 15;
        imgGrp = new KtcGrpAss(x,y,wg,tabCol[ccol][cli],nodeData,nodeData.Groups[gi], stage);
        dimGrps[ccol][cli] = imgGrp.getDim();
        if (w < dimGrps[ccol][cli].pos.x + dimGrps[ccol][cli].size.width) {w = dimGrps[ccol][cli].pos.x + dimGrps[ccol][cli].size.width;};
        if (h < dimGrps[ccol][cli].pos.y + dimGrps[ccol][cli].size.height) {h = dimGrps[ccol][cli].pos.y + dimGrps[ccol][cli].size.height;};
    };
    w += spw;
    h += (3*r + 10);
    if (w < 300) {w = 300;};
    if (w < stage.width()) {
        stage.width(w);
        $('#'+idDiv).width(w);
    } else {
       w = stage.width(w)
        };
    $('.modal-dialog').width(w+40);
    stage.height(h);
    $('#'+idDiv).height(h);
    ccol = 0;
    var yCarou = h - (2*r+10);
    stage.carouLayer.y(yCarou);
    stage.elemsLayer.y(yCarou);
    for (var ni=0; ni < nodesData.length; ni++) {
        if (nodesData[ni].NodeID != nodeData.NodeID) {
            x = (ccol * (wn+spw)) + r + 4;
            y = r + 5,
            new KtcNodeGrp(x,y,r,nodesData[ni], 0, stage.elemsLayer);
            ccol++;
        };
    };
    stage.carouLayer.speed = 1;
    KtcInitCarouselNodes(r, x+r, stage)
    stage.draw();
};

// Helper functions
function calculateDimGrps(nbColGrp, nbLiGrp, groups, hSize) {
    var nbCol = 4, hHead = 50, r = 25;
    var stepN = 2*r +10;
    var hb= hHead + 10;
    var sum, nl, ratio, size;
    var tabCol = new Array();
    for (var i= 0; i < nbColGrp; i++) {
        tabCol.push(new Array());
        for (var ii= 0; ii < nbLiGrp; ii++){tabCol[i].push(0);};
    };
    for (var cptCol = 0; cptCol < nbColGrp; cptCol++){
        sum = 0;
        nl =0;
        for (var cptLi = 0; cptLi < nbLiGrp; cptLi++){
            gi = cptCol + (nbColGrp * cptLi);
            if (gi < groups.length) {
                tabCol[cptCol][cptLi] = Math.ceil(groups[gi].maxAssociations / nbCol); // add necessary line count
                sum += tabCol[cptCol][cptLi] ;
                nl++;
            };
        };
        size = nl * hb + sum * stepN;
        ratio = (hSize/ size);
        if (ratio >= 1) {ratio = 1;
        } else {size = Math.ceil(size * ratio);};
        size = 0;
        for (var cptLi = 0; cptLi < nbLiGrp; cptLi++){
            tabCol[cptCol][cptLi] = Math.floor(tabCol[cptCol][cptLi] * ratio);
            if (tabCol[cptCol][cptLi] == 0) {tabCol[cptCol][cptLi]  =1;};
            size += tabCol[cptCol][cptLi] * stepN + hb;
        };
    };
    return tabCol;
};

function getFreePosGrp(tabN) {
    var retval = -1;
    for (i=0; i<tabN.length;i++){
        if (!tabN[i].kN) {
            retval = i;
            break;
        };
    };
    return retval;
};

function initGoAction (go) {
    go.on('mouseover touchstart', function() {
        var stage = this.getStage();
        document.body.style.cursor = "pointer";
        this.opacity(0.5);
        this.attrs.anim.start();
        stage.carouLayer.speed = 1;
        this.attrs.layer.draw();
        });
    go.on('mouseout touchend', function() {
        var stage = this.getStage();
        document.body.style.cursor = "default";
        this.opacity(1);
        this.attrs.anim.stop();
        stage.carouLayer.speed = 1;
        this.attrs.layer.draw();
    });
    go.on('click', function() {
        var stage = this.getStage();
        this.attrs.anim.stop();
        stage.carouLayer.speed = 1;
        this.opacity(1);
        this.attrs.layer.draw();
    });
};

function getLabelDevice(nodeZW) {
    if (nodeZW.Name != "Undefined" && nodeZW.Name !="") {
        return nodeZW.Name + '\n(' + nodeZW.NodeID +')';
    } else {
        return "Node " + nodeZW.NodeID;
    };
};

function wrapText(text, maxWidth) {
    var words = text.text().split(' ');
    var line = '';
    var lines = '';
    for(var n = 0; n < words.length; n++) {
      var testLine = line + words[n] + ' ';
      text.text(testLine);
      if (text.width() > maxWidth && n > 0) {
        lines += line + '\n';
        line = words[n] + ' ';
        if (n == words.length -1) {
          lines += line};
      }
      else {
        line = testLine;
        if (n == words.length -1) {
          lines += line};
      }
    }
    text.text(lines);
  }

function GetNewGroups (stage, node) {
//    console.log('get new grp for sending');
    var groups = stage.get('.ngroupass');
    for (var gnew= 0; gnew < groups.length; gnew++) {
        for (var g in node.Groups) {
            if (groups[gnew].attrs.grpAssP.grpAss.index == node.Groups[g].index) {
                node.Groups[g].members = groups[gnew].attrs.grpAssP.members;
                break;
            };
        };
    };

    return node.Groups;
};

function RefreshGroups(stage, newGroups) {
//    console.log("Refresh state members groups");
    var groups = stage.get('.ngroupass');
    for (var grp= 0; grp < groups.length; grp++) {
        for (var gn in newGroups) {
            if (groups[grp].attrs.grpAssP.grpAss.index == newGroups[gn].index) {
                groups[grp].attrs.grpAssP.members = newGroups[gn].members;
                for (var m in  groups[grp].attrs.grpAssP.tabN) {
                    if (groups[grp].attrs.grpAssP.tabN[m].kN) {
                        for (var mn =0; mn< newGroups[gn].members.length; mn++){
                           if (groups[grp].attrs.grpAssP.tabN[m].kN.nodeObj.NodeID == newGroups[gn].members[mn].node &&
                                groups[grp].attrs.grpAssP.tabN[m].kN.instanceAssoc == newGroups[gn].members[mn].instance) {
                                    groups[grp].attrs.grpAssP.tabN[m].kN.setState(newGroups[gn].members[mn].status);
                                    break;
                           };
                        };
                    };
               };
                break;
            };
        };
    };
    stage.draw();
};

// ************* Kinetic for Neighbors ********************

KtcLink = function (N1,N2,layer) {
    // build linelink
    var t = N1.getTypeLink();
    var qPts = N1.ktcGraph.findPath(N1, N2);
    this.calculatePos = false;
    var self = this;
    this.layer = layer;
    this.ktcNodes = new Array (N1, N2);
    var mirror = this.getMirrorLink();
        if (mirror) {
            mirror.attrs.ZwLink.link.attrs.qPts = qPts.to;
            mirror.attrs.ZwLink.link.attrs.org = qPts.dest;
            mirror.attrs.ZwLink.link.attrs.qPoints = qPts.points;
            mirror.attrs.ZwLink.calculatePos = false;
            mirror.attrs.ZwLink.link.attrs.curved = qPts.curved;
        };
    this.link = new Kinetic.Shape({
        id: 'link_'+N1.nodeZW.NodeID+'_to_'+N2.nodeZW.NodeID,
        stroke: t['color'],
        strokeWidth: t['indice'],
        lineCap: 'round',
        name: 'linknodes',
        qPts: qPts.from,
        org: qPts.org,
        qPoints: qPts.points,
        curved : qPts.curved,
        ZwLink: self,
        opacity:0.5,
        drawFunc: function(context) {
            if(this.attrs.ZwLink.ktcNodes[0].haslinktonode(this.attrs.ZwLink.ktcNodes[1].nodeZW)) {
                context.beginPath();
                context.moveTo(this.attrs.org.x, this.attrs.org.y);
                if (this.attrs.curved) {
                    context.quadraticCurveTo(this.attrs.qPts[0],this.attrs.qPts[1],this.attrs.qPts[2],this.attrs.qPts[3]);
                } else {
                    context.lineTo(this.attrs.qPts[2],this.attrs.qPts[3]);
                };
                context.fillStrokeShape(this);
                if(!this.attrs.ZwLink.ktcNodes[1].haslinktonode(this.attrs.ZwLink.ktcNodes[0].nodeZW)) {
                    if (this.tipLink == undefined) {
                        this.tipLink = new Kinetic.Group({
                          x: this.attrs.qPts[2],
                          y: this.attrs.qPts[3],
                          draggable: false,
                          opacity : 0.7,
                          name: 'tipLink'
                        });
                        this.textEnd = new Kinetic.Text({
                              x: 0,
                              y: 0,
                              text: this.attrs.ZwLink.ktcNodes[1].nodeZW.NodeID,
                              fontSize: 12,
                              fontFamily: 'Calibri',
                              fill: 'red',
                              name: 'textEnd'
                            });
                        this.textEnd.y((-this.textEnd.height()/2));
                        this.rectEnd = new Kinetic.Rect({
                            x: -2,
                            y: -((this.textEnd.height()/2)+2),
                            width: this.textEnd.width() + 4,
                            height: this.textEnd.height() + 4,
                            fill: "white",
                            stroke: 'red',
                            cornerRadius : 5,
                            name: 'rectEnd'
                        });
                        this.tipLink.add(this.rectEnd);
                        this.tipLink.add(this.textEnd);
                        this.parent.add(this.tipLink);
                    } else {
                        this.tipLink.x(this.attrs.qPts[2]);
                        this.tipLink.y(this.attrs.qPts[3]);
                        this.textEnd.text(this.attrs.ZwLink.ktcNodes[1].nodeZW.NodeID);
                    };
                } else if (this.tipLink != undefined) {
                        this.tipLink.destroyChildren();
                        this.tipLink.destroy();
                        this.tipLink = undefined;
                };
                var debug = false;
                    if (debug) {
                    if (this.curveDebug != undefined) {
                        this.curveDebug.destroyChildren();
                        this.curveDebug.destroy();
                        this.curveDebug = undefined
                    };
                    if (this.attrs.curved) {
                        color = 'red';
        //            } else {
        //                color = 'pink';};
                        this.curveDebug = new Kinetic.Group({
                              x: 0,
                              y: 0,
                              draggable: false,
                              name: 'debugLink'
                            });
                        for (p=0; p < this.attrs.qPoints.length; p+=2) {
                            this.curveDebug.add(new Kinetic.Circle({
                                x:this.attrs.qPoints[p].x,
                                y:this.attrs.qPoints[p].y,
                                radius: 2,
                                fill: color,
                                stroke: color,
                                strokeWidth: 1
                                })
                            );
                        };
                        this.parent.add(this.curveDebug);
                    };
                };
                this.attrs.ZwLink.calculatePos = true;
            };
        }
    });
    this.layer.add(this.link);
};

KtcLink.prototype.getMirrorLink = function(){
    var links = this.layer.getChildren();
    var searchId = 'link_'+this.ktcNodes[1].nodeZW.NodeID+'_to_'+this.ktcNodes[0].nodeZW.NodeID;
    for (i=0; i < links.length; i++) {
        var id = links[i].attrs.id;
        if (links[i].attrs.id == searchId) {
           return links[i];
        };
   }
   return false;
};

KtcLink.prototype.addnode = function(ktcNode) {
    var idx = this.ktcNodes.indexOf(ktcNode);
    if (idx == -1) {
        this.ktcNodes.push(ktcNode);
        ktcNode.addnode(this);
        this.layer.draw();
    };
};

KtcLink.prototype.destroy = function () {
    if (this.link.tipLink != undefined) {
        this.link.tipLink.destroyChildren();
        this.link.tipLink.destroy();
        this.link.tipLink = undefined;
    };
    if (this.link.curveDebug != undefined) {
        this.link.curveDebug.destroyChildren();
        this.link.curveDebug.destroy();
        this.link.curveDebug = undefined
    };
    this.link.destroy();
};

KtcLink.prototype.removelink= function(ktcNode) {
    var idx = this.ktcNodes.indexOf(ktcNode);
    if (idx != -1) {
        this.ktcNodes.splice(idx, 1);
        ktcNode.removenode(this);
        this.layer.draw();
    };
};

KtcLink.prototype.asnode= function(ktcNode) {
    var id = this.ktcNodes.indexOf(ktcNode);
    if (id1 != -1) {return true;
    }else {return false};
};

KtcLink.prototype.follownode = function(ktcNode, qPts) {
    var id = this.ktcNodes.indexOf(ktcNode);
    if (id != -1) {
        this.link.attrs.qPts = qPts.from;
        this.link.attrs.org = qPts.org;
        this.link.attrs.qPoints = qPts.points;
        var mirror = this.getMirrorLink();
        if (mirror) {
            mirror.attrs.ZwLink.link.attrs.qPts = qPts.to;
            mirror.attrs.ZwLink.link.attrs.org = qPts.dest;
            mirror.attrs.ZwLink.link.attrs.qPoints = qPts.points;
            mirror.attrs.ZwLink.calculatePos = false;
            mirror.attrs.ZwLink.link.attrs.curved = this.link.attrs.curved;
        };
    };
    return this.layer;
};

KtcLink.prototype.update= function() {
    var t = this.ktcNodes[0].getTypeLink();
    this.link.setStrokeWidth (t['indice']);
    this.link.setStroke(t['color']);
    this.layer.draw();
};

ktcScrollbar = function (contenaire, direction, layer) {
    this.ktcParent = contenaire;
    this.direction = direction;
    var thick = 16;
    var length = 130;
    if (this.ktcParent.ktcStage.nodeType = "Stage") {
        thick = 16;
        length = 130;
    };
    if (direction == 'horizontal') {
        length = (this.ktcParent.ktcStage.getWidth() - thick)  / 3; //130;
        var xOrg = 0, yOrg = this.ktcParent.ktcStage.getHeight() - thick;
        var areaWidth = this.ktcParent.ktcStage.getWidth() - thick;
        var areaHeight = thick;
        var barWidth = length;
        var barHeight = thick;
        var xBar = (areaWidth - barWidth)/2;
        var yBar = yOrg;
    } else {
        length = (this.ktcParent.ktcStage.getHeight() - thick)  / 3; //130;
        var xOrg = this.ktcParent.ktcStage.getWidth() - thick, yOrg = 0;
        var areaWidth = thick;
        var areaHeight = this.ktcParent.ktcStage.getHeight() - thick;
        var barWidth = thick;
        var barHeight = length;
        var xBar = xOrg ;
        var yBar = (areaHeight - barHeight)/2;
    };
    this.scrollArea = new Kinetic.Rect({
        x: xOrg,
        y: yOrg,
        width: areaWidth,
        height:areaHeight,
        fill: "black",
        opacity: 0.3,
        name: 'scrollbar'
    });
    this.scrollBar = new Kinetic.Rect({
        x: xBar,
        y: yBar,
        width: barWidth,
        height: barHeight,
        fill: "#90C633",
        draggable: true,
        clearBeforeDraw: true,
        area : this,
        dragBoundFunc: function(pos) {
           if (this.attrs.area.direction == 'horizontal') { // horizontale
                var newX = 0;
                var maxX = this.attrs.area.scrollArea.getWidth() - this.getWidth();
                if ((pos.x > 0) && ( pos.x < maxX)) {
                    newX = pos.x;
                } else if (pos.x > maxX) {
                    newX = maxX;
                };
                return {
                    x: newX,
                    y: this.getY()
                };
            } else { // verticale
                var newY = 0;
                var maxY = this.attrs.area.scrollArea.getHeight() -  this.getHeight();
                if ((pos.y > 0) && ( pos.y < maxY)) {
                    newY = pos.y;
                } else if (pos.y > maxY) {
                    newY = maxY;
                };
                return {
                    x: this.getX(),
                    y: newY
                };
            };
        },
        opacity: 0.9,
        stroke: "black",
        strokeWidth: 1,
        name: 'scrollbar'
    });
    // scrollbars events assignation
    this.scrollBar.on("mouseover touchstart", function() {
        document.body.style.cursor = "pointer";
    });
    this.scrollBar.on("mouseout touchend", function() {
        document.body.style.cursor = "default";
    });
    this.scrollBar.on("dragmove", function() {
        var p = this.attrs.area.ktcParent.getNodesCenter();
        if (this.attrs.area.direction == 'horizontal') { // horizontale
            p.x = this.attrs.area.getScrollPosition();
        } else {
            p.y = this.attrs.area.getScrollPosition();
        };
        this.attrs.area.ktcParent.setNodesCenter(p.x, p.y);
    });

    this.scrollBar.on("dragend", function() {
        this.attrs.area.ktcParent.nodeLayer.draw();
        this.attrs.area.ktcParent.linkLayer.draw();
    });

    layer.add(this.scrollArea);
    layer.add(this.scrollBar);
};

ktcScrollbar.prototype.reziseWidth = function (dw) {
    if (this.direction == 'horizontal') {
        var w = this.scrollArea.getWidth();
        var ratio = (w+dw) / w;
        var areaW = w + dw;
        this.scrollArea.setWidth(areaW);
        var length = areaW / 3;
        this.scrollBar.setX(this.scrollBar.getX() * ratio);
        this.scrollBar.setWidth(length);
        var offset = this.ktcParent.getNodesCenter();
        this.ktcParent.setNodesCenter(this.getScrollPosition(), offset.y);
    } else {
        this.scrollBar.setX(this.scrollBar.getX() + dw);
        this.scrollArea.setX(this.scrollArea.getX() + dw);
    };
};

ktcScrollbar.prototype.getScrollPosition = function () {
    if (this.direction == 'horizontal') {
        var areaW = this.scrollArea.getWidth();
        var length = areaW / 3;
        var scrollPos = (this.scrollBar.getX() + (length/2)) - (areaW/2);
        var ratio = this.ktcParent.space.width/ (areaW - length);
        var scrollPos = scrollPos * ratio ;
    } else {
        var areaW = this.scrollArea.getHeight();
        var length = areaW / 3;
        var scrollPos = (this.scrollBar.getY() + (length/2)) - (areaW/2);
        var ratio = this.ktcParent.space.height/ (areaW - length);
        var scrollPos = scrollPos * ratio ;
    };
    return scrollPos;
};

KtcNeighborsGraph = function (divId){
    var cont = $("#containerneighbors");
    var width = 800;
    for (var i=0; i < cont.length; i++) {
        if (cont[i].offsetWidth !== 0) {
            width = cont[i].offsetWidth - 30;
            break;
            };
        };
    this.ktcStage = new Kinetic.Stage({
        container: divId,
        width: width,
        height: 600,
        neighborsGraph : this
    });
    this.space = {width : 2000, height : 1000};
    this.nodeLayer = new Kinetic.Layer();
    this.linkLayer = new Kinetic.Layer();
    this.scrollLayer = new Kinetic.Layer();

    this.tooltip = new Kinetic.Label({
        x: 0,
        y: 0,
        draggable: false
    });
    this.tooltip.add(new Kinetic.Tag({
        fill: '#81DAF5',
        stroke: '#333',
        shadowColor: 'black',
        shadowBlur: 10,
        shadowOffset: {x:8,y:8},
        shadowOpacity: 0.5,
        lineJoin: 'round',
        pointerDirection: 'down',
        pointerWidth: 10,
        pointerHeight: 20,
        cornerRadius: 10
    }));
    this.tooltip.add(new Kinetic.Text({
        text: "Not Init",
        fontSize: 12,
        fontFamily: "Calibri",
        fill: "black",
        align : "left",
        padding: 3
    }));

    this.tooltipLayer = new Kinetic.Layer();
    this.buildKineticNeighbors();
    var graph = this
    window.onresize = function resizeStage(){
        var cont =  document.getElementById(divId);
        var w = cont.getBoundingClientRect();
        var dw = (w.width - 25) - graph.ktcStage.getWidth() ;
        graph.ktcStage.setWidth(w.width - 25);
        graph.hScrollBar.reziseWidth(dw);
        graph.vScrollBar.reziseWidth(dw);
     };
};

KtcNeighborsGraph.prototype.buildKineticNeighbors = function () {
    var L = this.linkLayer.get('.linknodes');
    L.each(function(node) {
        node.destroy();
        });
    L = this.nodeLayer.get('.picturenode');
    L.each(function(node) {
         node.destroy();
       });
    L = this.scrollLayer.get('.scrollbar');
    L.each(function(node) {
         node.destroy();
       });
    this.scrollLayer.removeChildren();
    this.tooltipLayer.removeChildren();
    this.linkLayer.offsetX(0);
    this.linkLayer.offsetY(0);
    this.nodeLayer.offsetX(0);
    this.nodeLayer.offsetY(0);
    this.ktcStage.removeChildren();
    this.hScrollBar = new ktcScrollbar(this, "horizontal", this.scrollLayer);
    this.vScrollBar = new ktcScrollbar(this, "vertical", this.scrollLayer);
    this.tooltipLayer.add(this.tooltip);
    var xc= this.ktcStage.getWidth() / 2;
    var yc= this.ktcStage.getHeight() / 2;
    var pos = [0, 0, 0];
    for (var i=0; i<nodesData.length;i++) {
        if (nodesData[i].Capabilities.indexOf("Primary Controller") != -1) {
            pos = [xc, yc, 0];
            r = 40;
        } else {
            pos = this.calculNodePosition(25, nodesData[i], pos[2]);
            r=25;
        };
        nodesData[i].ktcNode = new KtcNode(pos[0], pos[1], r, nodesData[i], this.nodeLayer, this);
      };
    for (var id1=0; id1<nodesData.length;id1++)  {
        for (var in1=0; in1<nodesData[id1].Neighbors.length;in1++) {
            nodeData2 = GetZWNode(nodesData[id1].NetworkID, nodesData[id1].Neighbors[in1]);
            if (nodeData2 && nodeData2.ktcNode != undefined) {
                var link = nodesData[id1].ktcNode.getLinkToNode(nodeData2.ktcNode);
                if (!link) {
                    link = new KtcLink(nodesData[id1].ktcNode, nodeData2.ktcNode, nodesData[id1].ktcNode.ktcGraph.linkLayer);
                    nodesData[id1].ktcNode.addlink(link);
                };
                nodeData2.ktcNode.addlink(link);
                link = nodeData2.ktcNode.getLinkToNode(nodesData[id1].ktcNode);
                if (!link) {
                    link = new KtcLink(nodeData2.ktcNode, nodesData[id1].ktcNode, nodesData[id1].ktcNode.ktcGraph.linkLayer);
                    nodeData2.ktcNode.addlink(link);
                };
                nodesData[id1].ktcNode.addlink(link);
            };
        };
    };
    this.ktcStage.add(this.linkLayer);
    this.ktcStage.add(this.nodeLayer);
    this.ktcStage.add(this.tooltipLayer);
    this.ktcStage.add(this.scrollLayer);
};

KtcNeighborsGraph.prototype.addNode = function(nodeData) {
    if (nodeData.Capabilities.indexOf("Primary Controller") != -1) {
        var r = 40;
        pos = [xc, yc, 0];
    } else {
        var r = 25;
        pos = this.calculNodePosition(r, nodeData, 0);
    };
    nodeData.ktcNode = new KtcNode(pos[0], pos[1], r, nodeData, this.nodeLayer, this);
    for (var in1=0; in1<nodeData.Neighbors.length;in1++) {
        nodeData2 = GetZWNode(nodeData.NetworkID, nodeData.Neighbors[in1]);
        if (nodeData2 && nodeData2.ktcNode != undefined) {
            var link = nodeData.ktcNode.getLinkToNode(nodeData2.ktcNode);
            if (!link) {
                link = nodeData2.ktcNode.getLinkToNode(nodeData.ktcNode);
                if (!link) {
                    link = new KtcLink(nodeData.ktcNode, nodeData2.ktcNode, this.linkLayer);
                };
            };
            nodeData.ktcNode.addlink(link);
            nodeData2.ktcNode.addlink(link);
        };
    };
    this.nodeLayer.batchDraw();
    this.linkLayer.batchDraw();
};

KtcNeighborsGraph.prototype.getNodesCenter = function () {
    return this.nodeLayer.getOffset();
};

KtcNeighborsGraph.prototype.setNodesCenter = function (x, y) {
    this.linkLayer.offsetX(x);
    this.linkLayer.offsetY(y);
    this.nodeLayer.offsetX(x);
    this.nodeLayer.offsetY(y);
    this.nodeLayer.batchDraw();
    this.linkLayer.batchDraw();
};

KtcNeighborsGraph.prototype.getNodesPos = function (s) {
    var nodesPos = [];
    var size;
    for (n in nodesData) {
        if (nodesData[n].ktcNode != undefined) {
//            pos = nodesData[n].ktcNode.pictureNode.position();
            pos = nodesData[n].ktcNode.position();
            size = nodesData[n].ktcNode.size();
            if (size.width == 0) {
                size.width = s;
                size.height = s;
            };
            nodesPos.push({"ktcNode": nodesData[n].ktcNode,
                    "gRect": {"x1": pos.x - (size.width /2), "y1": pos.y - (size.height /2), "x2": pos.x + (size.width /2), "y2": pos.y + (size.height /2)},
                    "force" : getGraphForce(nodesData[n])});
        };
    };
    return nodesPos;
};

KtcNeighborsGraph.prototype.calculNodePosition = function (rNode, nodeData, lastAngle) {
    var nodesPos = this.getNodesPos(2 * rNode);
    var xc= this.ktcStage.getWidth() / 2;
    var yc= this.ktcStage.getHeight() / 2;
    var minF = getMinForce();
    if (lastAngle == undefined) {var angle = 0;
    } else { angle = lastAngle; };
    var x=0, y=0;
    var nb = 0, nbLap = 1;
    var find = false, intersec = false;
    var force = minF + getGraphForce(nodeData);
    var stepA = 2 * Math.asin((4*rNode)/(2*force));
//    console.log("Node position ("+nodeData.NodeID+"), force "+force);
    while (!find) {
        angleC = angle;
        x= xc + force * Math.cos(angle);
        y= yc + force * Math.sin(angle);
        if (angle >= (2*Math.PI)) { // A covered lap and no position find
            angle = angle - (2*Math.PI);
            if (nbLap == 10) { // position find for A n lap. Increases force
                minF = minF + rNode;
                force = minF + getGraphForce(nodeData);
                stepA = 2 * Math.asin((4*rNode)/(2*force));
                nbLap = 1;
//                console.log("      Node position, No solution on this lap. Change force " + force);
            } else { nbLap++
//                console.log("      Node position, New lap " + nbLap);
                };
        } else {
            angle += stepA;
        };
        // check if position not interfer with other node.
        x1 = x - rNode, y1 = y - rNode, x2 = x + rNode, y2 = y + rNode;
        intersec = false;
        if (nodesPos.length != 0 ) {
            for (np in nodesPos) {
                if (nodesPos[np].ktcNode.nodeZW.NodeID != nodeData.NodeID) {
                    if (pointInRect(x1, y1, nodesPos[np].gRect) || pointInRect(x1, y2, nodesPos[np].gRect) ||
                        pointInRect(x2, y1, nodesPos[np].gRect) || pointInRect(x2, y2, nodesPos[np].gRect)) {
                            intersec = true;
                            break;
                    };
                };
            };
        };
        if (!intersec) { find = true; };
        nb++;
        if (nb > 256) { find = true; };
    };
//    console.log("   Node position, nb iteration :" +nb + " angle " + angleC *(180/Math.PI) + "°");
    return [x, y, angle];
};

KtcNeighborsGraph.prototype.findPath = function (kN1, kN2){
    var nodesPos = this.getNodesPos(50);
    var p1 = kN1.position()
    var p2 = kN2.position()
    var xm = (p1.x+p2.x)/2 , ym = (p1.y + p2.y) / 2;
    var pmT = {"x": xm, "y": ym};
    var qPts = {"org": {"x": p1.x, "y": p1.y},
                "dest" :{"x": p2.x, "y": p2.y},
                "from": [0, 0, xm, ym],
                "to":[0, 0, xm, ym],
                "points": getLinePoints(p1.x, p1.y, p2.x, p2.y),
                "curved": false};
    var tension = 0;
    var stepT = 5;
    var maxT = (Math.sqrt(Math.pow(p2.x-p1.x,2)+Math.pow(p2.y-p1.y,2)) / 2) - stepT;
    if (nodesPos.length != 0 ) {
        var solved = false;
        var nb =0;
        while (!solved) {
            solved = true;
            for (p in qPts.points) {
                for (np in nodesPos) {
                    if (nodesPos[np].ktcNode != kN1 && nodesPos[np].ktcNode != kN2){
                        if (pointInRect(qPts.points[p].x, qPts.points[p].y, nodesPos[np].gRect)) {
//                            console.log("    Point Position ("+qPts.points[p].x+","+qPts.points[p].y+") intersec node "+nodesPos[np].ktcNode.nodeZW.NodeID);
                            tension += stepT;
                            pmT = moveMedianPts(p1.x,p1.y, xm, ym, p2.x, p2.y, tension);
                            qPts = quadraticPoints(p1.x, p1.y, pmT.x, pmT.y, p2.x, p2.y);
                            solved = false;
                            break;
                        };
                    };
                };
                if (!solved) { break; };
            };
            if (Math.abs(tension) >= maxT) {
                if (Math.sign(tension) == -1) {
//                    console.log("Find Path have no solution with tension ("+kN1.nodeZW.NodeID+" to "+kN2.nodeZW.NodeID+")");
                    solved = true;
                } else {
                    tension = 0;
                    stepT = -5;
                };
            };
            if (nb > 200) {
//                console.log("Find Path have no solution, max iteration ("+kN1.nodeZW.NodeID+" to "+kN2.nodeZW.NodeID+")");
                solved = true};
            nb +=1;
        };
    };
    return qPts;
};

function pointInRect(x, y, gRect) {
    if ((x >= gRect.x1) && (x <= gRect.x2) && (y >= gRect.y1) && (y <= gRect.y2)) {
        return true;
    } else {
        return  false;
    };
};

function getGraphForce (nodeData) {
    return (100 - (nodeData.ComQuality)) * 10
};

function moveMedianPts (x1, y1, xm, ym, x2, y2, tension) {
    var a1 = (y2-y1)/(x2-x1);
    if (a1 == 0) {
        var a;
        var b = 0;
    } else {
        var a = -1/a1;
        var b = ym -(a*xm);
    };
    var len = Math.sqrt(Math.pow(x2-x1,2)+Math.pow(y2-y1,2));
    if (Math.abs(tension) >= len -10) {
        tension = Math.sign(tension)*(len -10);
    };
    return  getPointTension(xm, ym, a, b, tension);
};

function getLinePoints(x1, y1, x2, y2) {
    var a = (y2-y1)/(x2-x1);
    var b = y1 -(a*x1);
    var len = Math.sqrt(Math.pow(x2-x1,2)+Math.pow(y2-y1,2));
    var points = [];
    if (x1 < x2) {
        var x = x1;
        var y = y1;
    } else {
        var x = x2;
        var y = y2;
    };
    for (var l=10; l<len-10; l+=10) {
        points.push(getPointTension(x, y, a, b, l));
    };
    return points;
};

function getPointTension (x, y, a, b, tension) {
    // Solve quadratic eaquation
    var point = {"x": x, "y": y};
    if (tension !=0) {
        if (a != undefined) {
            var aa = (1+Math.pow(a,2));
            var bb = 2*((a*b)-(a*y)-x);
            var cc = Math.pow(x,2) + Math.pow(y,2) + Math.pow(b,2) - Math.pow(tension,2) - (2*y*b);
            var dd = Math.pow(bb,2)- (4*(aa*cc)); // discriminant
            var x2 = x;
            if (dd < 0) {
    //            console.log("Humm annoying, no solution ");
            } else if (dd == 0) {
    //            console.log("One solution ");
                x2 = -bb/(2*aa);
            } else if (tension > 0) {
    //            console.log("First solution ");
                x2 = (-bb + Math.sqrt(dd))/(2*aa)
            } else {
    //            console.log("Second solution ");
                x2 = (-bb - Math.sqrt(dd))/(2*aa)
            };
            point = {"x": x2, "y": (a*x2)+b};
        } else {
            point = {"x": x, "y": y + tension};
        };
    };
    return point;
};

function quadraticPoints (x1, y1, xm, ym, x2, y2) {
    var mL1 = {'x': (x1+xm)/2, 'y': (y1+ym)/2};
    var mL2 = {'x': (xm+x2)/2, 'y': (ym+y2)/2};
    var a1 = (ym-y1)/(xm-x1);
    var a2 = (y2-ym)/(x2-xm);
    var a = (y2-y1)/(x2-x1);
    var bm = ym-(a*xm);
    var len = Math.abs(Math.sqrt(Math.pow(x2-x1,2)+Math.pow(y2-y1,2))) / 2;
    if (a1 == 0) {
        var x1p = mL1.x;
    } else {
        var a1p = -1/a1;
        var b1p = mL1.y - (a1p*mL1.x);
        var x1p = (b1p-bm)/(a-a1p);
    };
    var y1p = (a*x1p) + bm;

    if (a2 == 0) {
        var x2p =mL2.x
    } else {
        var a2p =  -1/a2;
        var b2p = mL2.y - (a2p*mL2.x);
        var x2p = (b2p-bm)/(a-a2p);
    };
    var y2p = (a*x2p) + bm;

    var tab1 = [];
    var tab2 = [];
    for (var l=10; l<len-10; l+=10) {
        t = l/len;
//        t3b = Math.pow(1 - t, 3);
//        t2b = 3 * Math.pow(1 - t, 2) * t;
//        t2 = 3 * (1 - t) * Math.pow(t, 2);
//        t3 = Math.pow(t, 3);
//        x = t3b * x1 + t2b* x1p + t2 * x1p + t3 * xm;
//        y = t3b * y1 + t2b* y1p + t2 * y1p + t3 * ym;
        var t2 = Math.pow(t,2);
        var t2b =  Math.pow(1 - t, 2);
        var tbt = 2*(1-t)* t;
        x = t2b * x1 + tbt * x1p + t2 * xm;
        y = t2b * y1 + tbt * y1p + t2 * ym;
        tab1.push({"x": x, "y": y});
//        x = t3b * xm + t2b* x2p + t2 * x2p + t3 * x2;
//        y = t3b * ym + t2b* y2p + t2 * y2p + t3 * y2;
        x = t2b * xm + tbt * x2p + t2 * x2;
        y = t2b * ym + tbt * y2p + t2 * y2;
        tab2.push({"x": x, "y": y});
    };
    var tab = tab1.concat(tab2);
    return {"org":{"x": x1, "y": y1}, "dest":{"x": x2, "y": y2}, "from":[x1p, y1p, xm, ym], "to":[x2p, y2p, xm, ym], "points":tab, "curved": true}
};

// Points are objects with x and y properties
// p0: start point
// p1: 1st crossing point
// p2: 2nd crossing point
// p3: end point
// t: progression along curve 0..1
// returns an object containing x and y values for the given t
function bezierCubicXY (p0, p1, p2, p3, t) {
    var ret = {};
    var coords = ['x', 'y'];
    var i, k;

    for (i in coords) {
        k = coords[i];
        ret[k] = Math.pow(1 - t, 3) * p0[k] + 3 * Math.pow(1 - t, 2) * t * p1[k] + 3 * (1 - t) * Math.pow(t, 2) * p2[k] + Math.pow(t, 3) * p3[k];
    }
    return ret;
}

function setupContextMenuNode(self) {
    $.contextMenu('destroy', '#'+self.attrs.ktcNode.ktcGraph.ktcStage.attrs.container.id);
    var nodeData = self.attrs.ktcNode.nodeZW;
    $.contextMenu({
        selector: '#'+self.attrs.ktcNode.ktcGraph.ktcStage.attrs.container.id,
        className:'ktcNodeMenu-title',
        callback: function(key, options) {
            console.log("start request") + key;
            switch (key) {
                case 'HealNode' :
                case 'RefreshNodeInfo' :
                case 'RefreshNodeState' :
                case 'RefreshNodeDynamic' :
                    requestRefreshNode(key, nodeData);
                    break;
                case "updassoc" :
                    openDialogAssoc(nodeData);
                    break;
            };
        },
        items: {
            updassoc: {
                name: "Edit Associations",
                icon: function(){
                    return 'context-menu-icon contextmenu-icon-fa fa-link';
                },
                disabled:  (nodeData.Groups.length > 0) ? false : true,
                },
            sep1: "---------",
            HealNode: {
                name: "Heal node with reroute",
                icon: function(){
                    return 'context-menu-icon contextmenu-icon-fa fa-road';
                    }
                },
            RefreshNodeInfo: {
                name:"Refresh node informations",
                icon: function(){
                    return 'context-menu-icon contextmenu-icon-fa fa-info';
                    }
                },
            RefreshNodeState: {
                name: "Refresh state node",
                icon: function(){
                    return 'context-menu-icon contextmenu-icon-fa fa-check';
                    }
                },
            RefreshNodeDynamic: {
                name: "Refresh dynamics data",
                icon: function(){
                    return 'context-menu-icon contextmenu-icon-fa fa-spinner';
                    }
                },
            sep2: "---------",
            quit: {
                name: "Quitter", icon: function(){
                return 'context-menu-icon context-menu-icon-quit';
                }
            }
        },
        events: {
            hide: function(options){
                $.contextMenu('destroy', '#'+nodeData.ktcNode.ktcGraph.ktcStage.attrs.container.id);
                return true;
            }
        }
    });
    $('.ktcNodeMenu-title').attr('data-menutitle', getLabelDevice(self.attrs.ktcNode.nodeZW));
};

function openDialogAssoc(nodeData) {
    var bdiag = bootbox.dialog({
        show: false,
   //     size: 'small',
        className: 'text-center',
        title: 'Edit associations groups.' + "<br> " + nodeData.Model + " " + nodeData.NetworkID + '.' + nodeData.NodeID,
        message:  "<div class='contenaire-fluid'>" +
                        "<div id='contgrpass'>" +
                        "</div>" +
                    "</div>",
        data: nodeData,
        buttons: [{
            id: 'btn-cancel',
            label: 'Quit',
            className: 'btn-danger',
            autospin: false,
            callback: function(dialogRef){
//                                            console.log("Exit edit association.");
                ws.onmessage = ws_onmessage_diaggrp;
            }
        },{
            id: 'btn-sendchange',
            label: 'Send modification',
            className: 'btn-primary',
            autospin: false,
            callback: function(dialogRef){
                var grps =[];
                var newgrps = bdiag.getnewgroups();
                for (var i=0; i<newgrps.length; i++){
                    grps.push({'idx': newgrps[i].index, 'mbs': newgrps[i].members});
                };
                document.body.style.cursor = "wait";
                $('#btn-cancel').addClass('disabled');
                sendRequest("ozwave.node.set", {"key": "groups", "networkId": nodeData.NetworkID, "nodeId": nodeData.NodeID, 'ngrps': JSON.stringify(grps)}, function(data, result) {
                    var nodeRefId = GetNodeRefId(data.content.NetworkID, data.content.NodeID);
                    document.body.style.cursor = "default";
                    $('#btn-cancel').removeClass('disabled');
                    if (result == "error" || data.result == "error") {
                        new PNotify({
                            type: 'error',
                            title: 'Set group association fail.',
                            text: data.content.error,
                            delay: 6000
                        });
                    } else {
                        nodeData = RefreshGroupsNodeData(data.content.NetworkID, data.content.NodeID, data.content.groups);
                        RefreshGroups(bdiag.stageGrps, data.content.groups);
                        new PNotify({
                            type: 'success',
                            title: 'Set group association',
                            text: 'Association modification are sended.',
                            delay: 4000
                        });
                    };
                });
                return false;
            }
        }],
        onEscape: function() {
            ws.onmessage = ws_onmessage_diaggrp;
        },
    });
    bdiag.stageGrps = createKineticsGrpAssoc('contgrpass', nodeData);
    bdiag.getnewgroups = function () {
        var newgrps =  GetNewGroups(this.stageGrps, nodeData);
        return newgrps;
    };
    var ws_onmessage_diaggrp = ws.onmessage;
    ws.onmessage = function(e) {
        ws_onmessage_diaggrp(e);
        var data = JSON.parse(e.data);
        if (data.msgid == "ozwave.ctrl.report" && data.content.type == "node-state-changed" && data.content.data.state == "GrpsAssociation") {
            nodeData = RefreshGroupsNodeData(nodeData.NetworkID, nodeData.NodeID, data.content.data.Groups);
            RefreshGroups(bdiag.stageGrps, data.content.data.Groups);
            new PNotify({
                            type: 'success',
                            title: 'Set group association',
                            text: 'Association modification confirmed by node.',
                            delay: 4000
                        });
        };
    };
    bdiag.modal('show');
}

function addInGrpAssoc(grpAssP, kNode) {
    if (grpAssP.nodeOwner.MultiInstanceAssoc && Object.keys(kNode.nodeObj.Instances).length > 1) {
        if (grpAssP.members.length < grpAssP.grpAss.maxAssociations) {
            var listI = '<li><a instance="0" type="instance" href="#"><i class="fa fa-caret-right"></i> 0 : for use default instance</a></li>';
            for (i in kNode.nodeObj.Instances) {
                listI += '<li><a instance="'+i+'" type="instance" href="#"><i class="fa fa-caret-right"></i> '+
                            i+' for : '+kNode.nodeObj.Instances[i]+'</a></li>';
            };
            var bdiag = bootbox.dialog({
                show: false,
                size: 'small',
                className: 'text-center',
                title: 'Select instance of node <b>'+ kNode.nodeObj.NetworkID + '.' + kNode.nodeObj.NodeID + '</b> to associate it',
                message: '<div class="row">  ' +
                               "<div class='col-md-12'> " +
                                    "<div class='dropdown'> "+
                                        '<button class="btn btn-default dropdown-toggle" type="button" id="selectinstance" data-toggle="dropdown" aria-haspopup="true" aria-expanded="true">' +
                                            'Select an instance' +
                                            '<span class="caret"></span>' +
                                        ' </button>' +
                                        '<ul class="dropdown-menu" aria-labelledby="typerefresh">' +
                                            listI +
                                        '</ul' +
                                    '</div> ' +
                                "</div>"+
                            "</div>",
                data: {grpAssP: grpAssP, kNode: kNode},
                buttons: [{
                    id: 'btn-cancel',
                    label: 'Cancel',
                    className: 'btn-danger',
                    autospin: false,
                    callback: function(dialogRef){
                        kNode.pictNodeGrp.removeChildren();
                        delete(kNode.pictNodeGrp.attrs.nodeP);
                        delete(kNode.pictNodeGrp);
                        grpAssP.fondImg.stroke('black');
                        grpAssP.layer.getStage().draw();
                    }
                }]
            });
            bdiag.on("shown.bs.modal", function() {
                $("[type='instance']").click(function() {
//                    console.log("set Instance Asssoc : " + kNode.nodeObj.NetworkID+ "." + kNode.nodeObj.NodeID);
                    var instance = parseInt($(this).attr("instance"));
                    bdiag.modal('hide');
                    if (grpAssP.addNode(kNode, instance)) {
                        kNode.pictNodeGrp.attrs.nodeP.grpAss = grpAssP;
                        kNode.pictNodeGrp.attrs.nodeP.setState('to update', grpAssP);
                        grpAssP.nodeArea.add(kNode.pictNodeGrp);
                    } else {
//                        console.log('En doublons, suppression de la copie');
                        kNode.pictNodeGrp.removeChildren();
                        delete(kNode.pictNodeGrp.attrs.nodeP);
                        delete(kNode.pictNodeGrp);
                    };
                    grpAssP.fondImg.stroke('black');
                    grpAssP.layer.getStage().draw();
                });
            });
            bdiag.modal('show');
        };
    } else {
        if (grpAssP.addNode(kNode, 0)) {
            kNode.pictNodeGrp.attrs.nodeP.grpAss = grpAssP;
            kNode.pictNodeGrp.attrs.nodeP.setState('to update', grpAssP);
            grpAssP.nodeArea.add(kNode.pictNodeGrp);
        } else {
//            console.log('En doublons, suppression de la copie');
            kNode.pictNodeGrp.removeChildren();
            delete(kNode.pictNodeGrp.attrs.nodeP);
            delete(kNode.pictNodeGrp);
        };
        grpAssP.fondImg.stroke('black');
        grpAssP.layer.getStage().draw();
    };
};
