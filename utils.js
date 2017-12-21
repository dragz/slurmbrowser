
// this is dependent on underscore.js 

function create_numbers(explist) {
    var numbers;
    if ( explist.includes('-') ) {
	var r = explist.split('-');
	numbers = _.range(parseInt(r[0]), parseInt(r[1])+1);
    }
    else {
	numbers = explist;
    }
    return numbers;
}

function parsenodes1(nodespec) {
    // parse expressions like node[1,2,3-5]
    var base = (/[^\[]+/g).exec(nodespec).toString();
    var expansion = (/\[.*\]/).exec(nodespec);
    var exp_nl = [];
    if ( expansion ) {
	var explist = expansion.toString().slice(1, -1).split(',');
	var nodenumbers = _.flatten(explist.map(create_numbers));
	var compose_fullname = function(n) { return base+n;};
	exp_nl.push(nodenumbers.map(compose_fullname));
    }
    else {
	exp_nl.push(base);
    }
    return exp_nl;
}

function expand_nodelist(nodelist) {
    // split node elements on outmost commas
    var sep = /,(?=[a-z])/gi;
    var nl = nodelist.split(sep);
    var exp_nl = nl.map(parsenodes1);
    return _.flatten(exp_nl)
}

//var nodelist = "c1-[0-5],c2-[1,2,5-6,7-20],c3-1,c3-2,c4-[1,2,4,6]";
//document.getElementById('nodelist').innerHTML = nodelist;
//document.getElementById('expand_nodelist').innerHTML = expand_nodelist(nodelist);
