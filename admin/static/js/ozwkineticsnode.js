// Neighboors and group association library for showing zwave ode device.
var grpsStage;

var nodeStateColor = {'inCarou' : [0, "#E9FBAA", 1, "#DCD100"],         // yellow
                                'inCarouSelect': [0, "#685CDA", 1, "#1200B5"], // blue
                                'inGrp': [0, "#FFA9FF", 1, "#DC00D9"],              // pink
                                'inGrpSelect': [0, "#FC9090", 1, "#D00000"]     // red
                               };

KtcNode = function  (x, y, r, nodeZW, layer, graph) {
    this.nodeZW = nodeZW;
    this.ktcGraph = graph;
    this.pictureNode = new Kinetic.Group({
          x: x,
          y: y,
          draggable: true,
          name: 'picturenode',
          ktcNode : this
        });
    var op =1;
    if (this.nodeZW['State sleeping']) {op = 0.3; };
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
        shadowOffset: 5,
        shadowOpacity: 0.5,
        name:"pictureImg",
        opacity: op,
        ktcNode : this
        });
    var t = getLabelDevice(this.nodeZW);
    if (t.length > ((2*r)/5)) { yt = 8-r;
    } else {yt = -5;};
    this.text = new Kinetic.Text({
        x: -r +2,
        y: yt,
        width:2*r-4,
        text: t,
        fontSize: 12,
        fontFamily: "Calibri",
        fill: "black",
        align : "center"
    });
    this.pictureNode.add(this.pictureImg);
    this.pictureNode.add(this.text);
    this.links = new Array ();
    this.layer = layer;
    this.pictureNode.on("mouseover touchstart", function() {
        var img = this.get(".pictureImg");
        img[0].setFillRadialGradientColorStops([0, 'turquoise', 1, 'blue']);
        img[0].opacity(0.5);
        this.parent.draw();
        document.body.style.cursor = "pointer";
        });

    this.pictureNode.on("mouseout touchend", function() {
        var img = this.get(".pictureImg");
        img[0].setFillRadialGradientColorStops(this.attrs.ktcNode.getColorState());
        this.attrs.ktcNode.ktcGraph.tooltip.hide();
        var op =1;
        if (this.attrs.ktcNode.nodeZW['State sleeping']) {op = 0.3; };
        img[0].opacity(op);
        this.parent.draw();
        this.attrs.ktcNode.ktcGraph.tooltipLayer.draw();
        document.body.style.cursor = "default";
    });

    this.pictureNode.on("dragmove", function() {
      for (var i=0; i<this.attrs.ktcNode.links.length;i++) {
          this.attrs.ktcNode.links[i].follownode(this.attrs.ktcNode);
      };
      this.moveToTop();
    });
    this.pictureNode.on("mousemove", function(){
        var mousePos = this.attrs.ktcNode.ktcGraph.ktcStage.getPointerPosition();
        this.attrs.ktcNode.ktcGraph.tooltip.setPosition(mousePos.x + 5, mousePos.y + 5);
        var t = this.attrs.ktcNode.nodeZW.Type + ', Quality : ' + this.attrs.ktcNode.nodeZW.ComQuality + '%';
        for (var i=0; i<this.attrs.ktcNode.nodeZW.Groups.length; i++) {
            if (this.attrs.ktcNode.nodeZW.Groups[i].members.length !==0) {
                t = t+ '\n associate with node : ';
                for (var ii=0; ii<this.attrs.ktcNode.nodeZW.Groups[i].members.length; ii++) {
                    t= t  + this.attrs.ktcNode.nodeZW.Groups[i].members[ii].id+ ',';
                };
            } else {
             t = t+ '\n no association ';
            };
            t = t + ' in index ' + this.attrs.ktcNode.nodeZW.Groups[i].index + ' named :' + this.attrs.ktcNode.nodeZW.Groups[i].label;
        };
        this.attrs.ktcNode.ktcGraph.tooltip.setText(t);
        this.attrs.ktcNode.ktcGraph.tooltip.show();
        this.attrs.ktcNode.ktcGraph.tooltipLayer.draw();
        mousePos=0;
    });
    this.layer.add(this.pictureNode);
};

KtcNode.prototype.addlink = function(linker) {
    var idx = this.links.indexOf(linker);
    if (idx == -1) {
        this.links.push(linker);
        linker.addnode(this);
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

KtcNode.prototype.checklinks= function() {
    var idn = -1;
    for (var idx in this.links) {
        if (this.links[idx].ktcNodes[1].nodeZW.NodeID != this.nodeZW.NodeID) {
            idn = this.nodeZW.Neighbors.indexOf(this.links[idx].ktcNodes[1].nodeZW.NodeID);
            if (idn == -1) { // Link must me removed
                this.links[idx].destroy();
                this.links.splice(idx, 1);
            };
        };
    };
    var create = true;
    for (idn in this.nodeZW.Neighbors) {
        create = true;
        for (idx in this.links) {
            if (this.links[idx].ktcNodes[1].nodeZW.NodeID == this.nodeZW.Neighbors[idn]) {
                create = false;
                break;
            };
        };
        if (create) {
            N2 = GetZWNode(this.nodeZW.NetworkID, this.nodeZW.Neighbors[idn]);
            if (N2) {new KtcLink(this, N2.ktcNode, this.ktcGraph.linkLayer);};
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
            colors = [0, 'orange', 0.5, 'brown', 1, 'violet'];
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

KtcNode.prototype.getTypeLink = function(Node2) {
    var indice = 1, color = 'green';
    if (this.nodeZW.Capabilities.indexOf("Primary Controller" ) != -1 ) { indice =8;  color ='blue'}
    if (this.nodeZW.Capabilities.indexOf("Routing") != -1) {indice = indice + 2;}
    if (this.nodeZW.Capabilities.indexOf("Beaming" ) != -1) {indice = indice + 1;}
    if (this.nodeZW.Capabilities.indexOf("Listening" ) != -1) { indice = indice + 3;}
    if (this.nodeZW.Capabilities.indexOf("Security") != -1) { color ='yellow';}
    if (this.nodeZW.Capabilities.indexOf("FLiRS") != -1) { indice = indice + 2;}
    if (this.nodeZW['State sleeping']) {indice = indice -2; color = 'orange';}
    if (this.nodeZW['InitState'] == 'Out of operation') {indice = 1,  color = 'red';}
    return {'indice' : indice, 'color' : color}
};

KtcNode.prototype.update = function() {
    this.checklinks();
    this.pictureImg.setFillRadialGradientColorStops(this.getColorState());
    this.ktcGraph.tooltip.hide();
    var op =1;
    if (this.nodeZW['State sleeping']) {op = 0.3; };
    this.pictureImg.opacity(op);
    for (var l in this.links)  {this.links[l].update();};
    this.pictureNode.draw();
    this.ktcGraph.tooltipLayer.draw();
    this.ktcGraph.linkLayer.draw();
    console.log('redraw kinetic node :' + this.nodeZW.NodeID);
};

// Groups associations functions

// Basic Kinetics objet for group association

KtcNodeGrp = function  (x, y, r, node, layer, grpAssociation) {
    this.pictNodeGrp = new Kinetic.Group({
          x: x,
          y: y,
          draggable: true,
          name : "nodegrp",
          nodeP : this
        });
    if (typeof(grpAssociation)=='undefined'){
        this.grpAss = layer;
        f = nodeStateColor.inCarou; //'yellow';
        } else {
        this.grpAss = grpAssociation;
        f = nodeStateColor.inGrp; //'pink';
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
    this.nodeObj = node;
    this.layer = layer;
    this.state = 'unknown';
    this.moveInGrp = undefined;
    var self = this;
    setTimeout(function () {
            if (self.grpAss == grpAssociation) {
            for (var i = 0; i<self.grpAss.grpAss.members.length; i++){
                 if (self.nodeObj.NodeID == self.grpAss.grpAss.members[i].id){
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
//        var stage = this.getStage();
        console.log("dragstart node :" + this.attrs.nodeP.nodeObj.NodeID);
        var newstate = 'unallowable';
        if (!this.attrs.nodeP.isMember()) {
            this.attrs.nodeP.duplicateIt()
            newstate = this.state;};
        this.attrs.nodeP.setState(newstate);
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
                this.attrs.nodeP.setState('to update', inGrp.attrs.grpAssP);
            } else {
                this.attrs.nodeP.setState('del');
            };
        };
        this.getStage().draw();
    });

    this.pictNodeGrp.on("dragend", function(e) {
        console.log("dragend node :" + this.attrs.nodeP.nodeObj.NodeID);
        var inGrp = this.attrs.nodeP.inGroup();
        this.attrs.nodeP.tooltip.hide();
        if (!this.attrs.nodeP.isMember()) {
            if (!inGrp){
                this.removeChildren();
                console.log("Hors d'un groupe, destruction de la copie.");
                delete(this.attrs.nodeP);
                delete(this);
            }else {
                console.log('dans un groupe, ajouter au groupe si pas doublon.');
                if (inGrp.attrs.grpAssP.addNode(this.attrs.nodeP)) {
                    this.attrs.nodeP.grpAss =inGrp.attrs.grpAssP;
                    this.attrs.nodeP.setState('to update');
                    inGrp.attrs.grpAssP.nodeArea.add(this);
             //       inGrp.attrs.grpAssP.refreshText();
                } else {
                    console.log('En doublons, suppression de la copie');
                    this.removeChildren();
                    delete(this.attrs.nodeP);
                    delete(this);
                };
                inGrp.attrs.grpAssP.fondImg.stroke('black');
            };
        } else {
            if ((inGrp==null) || (inGrp.attrs.grpAssP != this.attrs.nodeP.grpAss)){
                this.attrs.nodeP.grpAss.delNode(this.attrs.nodeP);
            //    inGrp.attrs.grpAssP.refreshText();
                this.removeChildren();
                console.log('Hors du groupe, node retiré du group et détruit');
            }else {
                console.log('toujours dans le groupe, remis à sa place.');
                this.x(this.attrs.nodeP.xOrg).y(this.attrs.nodeP.yOrg);
                };
            };
        this.getStage().draw();
    });

    this.pictNodeGrp.on("mousedown", function(e) {
        console.log("mousedown node :" + this.attrs.nodeP.nodeObj.NodeID);
        if (this.attrs.nodeP.isMember()) {
            console.log("move node outside to exclude it");
        };
        this.moveToTop();
    });

//    this.pictNodeGrp.on("mousemove touchmove", function(e){
//        this.attrs.nodeP.tooltip.hide();
//    });
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
    var n = new KtcNodeGrp(this.xOrg, this.yOrg, this.rOrg, this.nodeObj ,stage.elemsLayer);
    stage.draw();
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
                if (this.kImg) {this.kImg.hide();};
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
         var zstate = state, stOrg = false;
         var isMember = (this.grpAss != this.layer);
         if (isMember) {
             for (var i = 0; i<this.grpAss.grpAss.members.length; i++){
                 if (this.nodeObj.NodeID == this.grpAss.grpAss.members[i].id){
                    zstate = this.grpAss.grpAss.members[i].status;
                     stOrg  = true;
                    break;
                 };
             };
         };
         var isAMember = null;
         if (inGrpAss) {isAMember = inGrpAss.isAMember(this.nodeObj);};
         switch (state) {
            case 'add':
                if (isAMember || (inGrpAss.members.length >= inGrpAss.grpAss.maxAssociations)) {
                    this.setimgstate('unallowable');
                }else {this.setimgstate('add');};
                break;
            case 'del':
                this.setimgstate('del');
                break;
            case 'unallowable':
                this.setimgstate('unallowable');
                break;
            case 'to update':
                if (isAMember || stOrg) {this.setimgstate(zstate);
                } else {this.setimgstate('to update');};
                break;
       };
    } else {
         console.log("setState sur node persistant") ;
    };
};

KtcGrpAss = function (x,y,w, maxLi, nodeData, grp,stage) {
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
    var strmembers = '', sp='';
    for (var i in grp.members) {
        strmembers += sp + grp.members[i].id ;
        sp=', ';
    };
    this.infos = new Kinetic.Label({
        x: 3,
        y: 3,
        draggable: false
    });
    this.infos.add(new Kinetic.Text({
        height: w,
        text: "Group " + grp.index + ", " + grp.label + "\n Max members : "+grp.maxAssociations + "\n Members : " + strmembers,
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
        m = new KtcNodeGrp(this.tabN[posm].x,this.tabN[posm].y,r,GetZWNode(nodeData.NetworkID, grp.members[i].id),stage.grpsLayer,this);
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
        strmembers += sp + this.members[i].id ;
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

KtcGrpAss.prototype.isAMember = function (nodeObj) {
    var retval = null;
    for (var i=0; i<this.members.length; i++) {
        if (this.members[i].id == nodeObj.NodeID) {
            retval = this.members[i];
            break;
            };
    };
    return retval
};

KtcGrpAss.prototype.addNode = function (kNode) {
    if (!this.isAMember(kNode.nodeObj)) {
        if (this.members.length<this.grpAss.maxAssociations) {
            var state = 'to update';
            for (var i = 0; i<this.grpAss.members.length; i++){
                if (kNode.nodeObj.NodeID == this.grpAss.members[i].id){
                state = this.grpAss.members[i].status;
                break;
                };
            };
            this.members.push({id:kNode.nodeObj.NodeID, status: state});
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
                console.log ("Plus de place disponible, pas d'ajout");
                return false};
        }else {
            console.log ("Nombre max atteint, pas d'ajout");
            return false};
    } else { return false;};
};

KtcGrpAss.prototype.delNode = function (kNode) {
    var idx =-1;
    if (kNode.nodeObj) {
        for (var i =0; i< this.members.length; i++) {
            if (this.members[i].id == kNode.nodeObj.NodeID) {
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
            if (GetZWNode(kNode.nodeObj.NetworkID, this.members[i].id) == false) {
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
            new KtcNodeGrp(x,y,r,nodesData[ni] ,stage.elemsLayer);
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
       // var x = stage.elemsLayer.getX();
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
    console.log('get new grp for sending');
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
    console.log("Refresh state members groups");
    var groups = stage.get('.ngroupass');
    for (var grp= 0; grp < groups.length; grp++) {
        for (var gn in newGroups) {
            if (groups[grp].attrs.grpAssP.grpAss.index == newGroups[gn].idx) {
                for (var m in  groups[grp].attrs.grpAssP.tabN) {
                    if (groups[grp].attrs.grpAssP.tabN[m].kN) {
                        for (var mn =0; mn< newGroups[gn].mbs.length; mn++){
                           if (groups[grp].attrs.grpAssP.tabN[m].kN.nodeObj.NodeID == newGroups[gn].mbs[mn].id) {
                               var img = groups[grp].attrs.grpAssP.tabN[m].kN.kImg;
                               groups[grp].attrs.grpAssP.tabN[m].kN.setimgstate(newGroups[gn].mbs[mn].status, img);
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
