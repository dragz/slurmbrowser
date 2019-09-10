// this is dependent on lodash.js

function create_numbers(explist) {
  var numbers;
  if (explist.includes("-")) {
    var r = explist.split("-");
    numbers = _.range(parseInt(r[0]), parseInt(r[1]) + 1);
  } else {
    numbers = explist;
  }
  return numbers;
}

function parsenodes1(nodespec) {
  // parse expressions like node[1,2,3-5]
  var base = /[^\[]+/g.exec(nodespec).toString();
  var expansion = /\[.*\]/.exec(nodespec);
  var exp_nl = [];
  if (expansion) {
    var explist = expansion
      .toString()
      .slice(1, -1)
      .split(",");
    var nodenumbers = _.flattenDeep(explist.map(create_numbers));
    var compose_fullname = function(n) {
      return base + n;
    };
    exp_nl.push(nodenumbers.map(compose_fullname));
  } else {
    exp_nl.push(base);
  }
  return exp_nl;
}

function expand_nodelist(nodelist) {
  // split node elements on outmost commas
  var sep = /,(?=[a-z])/gi;
  var nl = nodelist.split(sep);
  var exp_nl = nl.map(parsenodes1);
  return _.flattenDeep(exp_nl);
}

//var nodelist = "c1-[0-5],c2-[1,2,5-6,7-20],c3-1,c3-2,c4-[1,2,4,6]";
//document.getElementById('nodelist').innerHTML = nodelist;
//document.getElementById('expand_nodelist').innerHTML = expand_nodelist(nodelist);

var timespec_to_seconds = function(data) {
  var days = 0,
    hours = 0,
    minutes = 0,
    seconds = 0;
  var s;
  // quick fix for interpreting bug i squeue data
  if (! data || typeof(data) === "number") {
    return 0;
  }
  if (data.includes("-")) {
    days = data.split("-")[0];
    s = data.split("-")[1];
  } else {
    s = data;
  }
  return (
    days * 24 * 3600 + s.split(":").reduce((acc, time) => 60 * acc + +time)
  );
};

$.fn.dataTable.ext.type.order["timespec-pre"] = function(d) {
  return timespec_to_seconds(d);
};

// copypasted from file-size sort plugin.
$.fn.dataTable.ext.type.order["mem-size-pre"] = function(data) {
  if (typeof(data) === 'number') {
    return data
  }
  var matches = data.match(/^(\d+(?:\.\d+)?)([a-z]+)/i);
  var multipliers = {
    b: 1,
    bytes: 1,
    kb: 1000,
    kib: 1024,
    k: 1024,
    mb: 1000000,
    mib: 1048576,
    m: 1048576,
    gb: 1000000000,
    gib: 1073741824,
    g: 1073741824,
    tb: 1000000000000,
    tib: 1099511627776,
    t: 1099511627776,
    pb: 1000000000000000,
    pib: 1125899906842624,
    p: 1125899906842624
  };

  if (matches) {
    var multiplier = multipliers[matches[2].toLowerCase()];
    return parseFloat(matches[1]) * multiplier;
  } else {
    return -1;
  }
};
