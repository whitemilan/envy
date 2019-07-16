 var socket = null;
 var isopen = false;
 var song_current = -1;
 var selectedSongs = [];

 window.onload = function() {
    socket = new WebSocket("ws://192.168.0.179:9000");
    socket.binaryType = "arraybuffer";
    socket.onopen = function() {
       console.log("Connected!");
       isopen = true;
    }
    socket.onmessage = function(e) {
      var message = {};
      if (typeof e.data == "string") {
          console.log("Text message received: " + e.data);
          message = JSON.parse(e.data);
          
	  if (message['alarms']) {
              var text = "";
	      for (i = 0; i < message["alarms"].length; i++) { 
                 text += "<option value=" + i + ">" + message["alarms"][i] + 
                         "</option>"
              }
              document.getElementById("delete_number").innerHTML=text;
	  }
          
	  if (message['playlists']) {
	      var text2 = "";
              for (i = 0; i < message["playlists"].length; i++) {
                  text2 += "<option value=\"" + message["playlists"][i]
                  + "\">" + message["playlists"][i] + 
                          "</option>"
              }
              document.getElementById("list_of_playlists").innerHTML=text2;
	  }
          if (message['songlist']) {
	      var text3 = '';
              for (i = 0; i < message['songlist'].length; i++) {
                  text3 += '<li data-ns='+ i +' onclick="selectSong(this)" draggable=true '
		  	    + 'ondblclick="jumpTo(this)" '
			    + 'ondragstart="dragstart(event, this)" '
			    + 'ondrag="drag(event, this)" '
			    + 'ondragenter="allowDrop(event, this)" '
			    + 'ondragend="dragend(event, this)">' 
			    + message['songlist'][i]+'</li>';
              }
              document.getElementById("songlist").innerHTML=text3;
	      var children = document.getElementById('songlist').childNodes;
	  }
	  if (message['status']) {
	      if (message['status']['state'] == 'play') {
		  document.getElementById('button_toggle').innerHTML= 'Pause';
	      } else {
		  document.getElementById('button_toggle').innerHTML= 'Play';
	      }
          var children = document.getElementById('songlist').childNodes;
	      if (message['status']['song']) {
		      var song_current_new = Number(message['status']['song']);
              if (song_current_new > -1 ) {
                if (song_current != song_current_new) {
                    if (song_current > -1) {
                        children[song_current].removeAttribute("style");
                    }
                    children[song_current_new].style.color = "red";
                    song_current = song_current_new;
                }
            }
	      }
	      else {
		      song_current = -1;
	      }
	      
	  }
	  if (message['ls']) {
		  var text3 = '<li onclick="openFolder(\'\')">..</li>';
		  for (i = 0; i < message['ls'][0].length; i++) {
			  text3 += '<li class="directory" onclick="openFolder(\''+message['ls'][0][i]+'\')">' + message['ls'][0][i] + '</li>';
		  }
		  for (i = 0; i < message['ls'][1].length; i++) {
			  text3 += '<li class="file" onclick="addFile(\''+message['ls'][1][i]+'\')">' + message['ls'][1][i] + '</li>';
		  }
		  document.getElementById("directorystructure").innerHTML=text3;
	  }
  
	  if (message['library']) {
//    	      document.getElementById("div_out2").innerHTML="Library got uptdated.";
	  }
// 	  document.getElementById("div_out2").innerHTML=message.value;
       } else {
          var arr = new Uint8Array(e.data);
          var hex = '';
          for (var i = 0; i < arr.length; i++) {
             hex += ('00' + arr[i].toString(16)).substr(-2);
          }
          console.log("Binary message received: " + hex);
       }
    }
    socket.onclose = function(e) {
       console.log("Connection closed.");
       socket = null;
       isopen = false;
    }
 };
 function sendCommand(task) {
    if (isopen) {
       var ab_msg = {task:task}
       var json_msg = JSON.stringify(ab_msg)
      
//        document.getElementById("div_msg2").innerHTML=json_msg;
       socket.send(json_msg);
       console.log("Text message sent.");               
    } else {
       console.log("Connection not opened. Reloading page.")
       location.reload(true)
    }
 };
 function sendBinary() {
    if (isopen) {
       var buf = new ArrayBuffer(32);
       var arr = new Uint8Array(buf);
       for (i = 0; i < arr.length; ++i) arr[i] = i;
       socket.send(buf);
       console.log("Binary message sent.");
    } else {
       console.log("Connection not opened.")
    }
 };
 
 function displayClock() {
    if (isopen) {
       document.getElementById('clockh').style.display = 'block';
    } else {
       console.log("Connection not opened. Reloading page.")
       location.reload(true)
    }
  
 };
 function collectHours(hours) {
    if (isopen) {
       alarm_hours = hours; 
       document.getElementById('clockh').style.display = 'none';
       document.getElementById('clockm').style.display = 'block';
    } else {
       console.log("Connection not opened. Reloading page.")
       document.getElementById('clockh').style.display = 'none';
       location.reload(true)
    }
 };
 function sendAlarm(alarm_minutes) {
    if (isopen) {
       var ab_msg = {task:"add_alarm", hours:alarm_hours, minutes:
           alarm_minutes};
       var json_msg = JSON.stringify(ab_msg);
//        document.getElementById("div_msg2").innerHTML=json_msg;
       socket.send(json_msg);
       document.getElementById('clockm').style.display = 'none';
       console.log("Text message sent.");               
    } else {
       console.log("Connection not opened.")
       document.getElementById('clockm').style.display = 'none';
       location.reload(true)
    }
};
function sendTimer(minutes) {
    if (isopen) {
        var ab_msg = {task:"add_alarm", hours: -1, minutes: minutes};
        var json_msg = JSON.stringify(ab_msg);
        socket.send(json_msg);
        console.log("Timer sendt.");
    } else {
        console.log("Connection not opened.")
    }
};
function sendDelete_Alarm() {
    if (isopen && document.getElementById("delete_number").value ) {
        var number_alarm =
                document.getElementById("delete_number").value;
        var ab_msg = {task:"delete_alarm", no_alarm:number_alarm};
        var json_msg = JSON.stringify(ab_msg);
        socket.send(json_msg);
        console.log("Text message sent.")
    }
};
function sendLoadPlaylist() {
    if (isopen && document.getElementById("list_of_playlists").value ) {
        var name_playlist =
                document.getElementById("list_of_playlists").value;
        var ab_msg = {task:"load_playlist", playlist:name_playlist};
        var json_msg = JSON.stringify(ab_msg);
//         document.getElementById("div_msg2").innerHTML=json_msg;
        socket.send(json_msg);
        console.log("Text message sent.")
    }
};
function sendDeletePlaylist() {
    if (isopen && document.getElementById("list_of_playlists").value ) {
        var name_playlist =
                document.getElementById("list_of_playlists").value;
        var ab_msg = {task:"delete_playlist", playlist:name_playlist};
        var json_msg = JSON.stringify(ab_msg);
//         document.getElementById("div_msg2").innerHTML=json_msg;
        socket.send(json_msg);
        console.log("Text message sent.")
    } 
};

function deleteSongs() {
    if (isopen) {
	if (selectedSongs.length > 0) {
	    var msg = {task: "delete_songs", selected_songs: selectedSongs};
            var json_msg = JSON.stringify(msg);
            socket.send(json_msg);
	    selectedSongs = [];
	}
    } else {
       	console.log("Connection not opened.")
       	location.reload(true)
    }
}

function selectSong(node) {
    var number_song = node.getAttribute('data-ns');
    var index_song = selectedSongs.indexOf(number_song)
    if (index_song != -1) {
	selectedSongs.splice(index_song, 1);
	//node.setAttribute("style", "background: #000;")
        node.style.background = '#000';
    } else {
	selectedSongs.push(number_song);
	//node.setAttribute("style", "background: #060;")
        node.style.background = '#060';
    }
//     document.getElementById("div_out2").innerHTML=selectedSongs;

}

function jumpTo(node) {
    if (isopen) {
	if (selectedSongs) {
    	    var number_song = node.getAttribute('data-ns');
	    var msg = {task: "jump_to", song: number_song};
            var json_msg = JSON.stringify(msg);
            socket.send(json_msg);
	}
    } else {
       	console.log("Connection not opened.")
       	location.reload(true)
    }
}

function allowDrop(ev, node) {
    ev.preventDefault();
    deletePlaceholder();
    var newRow = node.insertAdjacentHTML('beforebegin', '<li id="ph" '
	+ 'data-ns='+(node.getAttribute('data-ns'))+' ondragleave="deletePlaceholder()" '
	+ 'ondragover="allowDropPlaceholder(event, this)" '
	+ 'ondrop="drop(event, this)" ></li>');
//     document.getElementById("div_out2").innerHTML="allow drop works";
}

function allowDropPlaceholder(ev, node) {
    ev.preventDefault();
}

function deletePlaceholder() {
    var placeholder = document.getElementById("ph");
    if (placeholder)
	placeholder.remove();
}
var song_dragged = -1;
function dragstart(ev, node) {
    // ev.dataTransfer.setData("number_song", node.value);
    song_dragged = node.getAttribute('data-ns');
}

function dragend(ev, node) {
    node.removeAttribute("style");
    deletePlaceholder();
//     document.getElementById("div_out2").innerHTML="Dragend works";
}

function drag(ev, node) {
//     document.getElementById("div_out2").innerHTML="Dragging...";
    node.style.display = 'none';
}


function drop(ev, node) {
    //ev.preventDefault();
    //var data = ev.dataTransfer.getData("number_song");
    if (isopen) {
	if (selectedSongs) {
    	    var number_song = song_dragged;
	    var number_destination = node.getAttribute('data-ns');
	    if (number_song < number_destination) {
		number_destination -= 1;
	    }
	    if ( song_current == number_song ) {
		song_current = number_destination;
	    }
	    var msg = {task: "move_songs", song: number_song, destination: number_destination};
            var json_msg = JSON.stringify(msg);
            socket.send(json_msg);
	    sendCommand('ask_for_status')
	}
    } else {
       	console.log("Connection not opened.");
       	location.reload(true);
    }
}

function openFolder(foldername) {
    if (isopen) {
	var msg = {task: "open_folder", folder: foldername};
        var json_msg = JSON.stringify(msg);
        socket.send(json_msg);
    } else {
       	console.log("Connection not opened.");
       	location.reload(true);
    }
}

function addFile(filename) {
    if (isopen) {
	var msg = {task: "add_file", file: filename};
        var json_msg = JSON.stringify(msg);
        socket.send(json_msg);
    } else {
       	console.log("Connection not opened.");
       	location.reload(true);
    }
}


function savePlaylist() {
    
    
    var name = document.getElementById('newPlaylistName').value;
    
    if (isopen) {
	var msg = {task: "save_playlist", playlistname: name};
        var json_msg = JSON.stringify(msg);
        socket.send(json_msg);
    } else {
       	console.log("Connection not opened.");
       	location.reload(true);
    }
}
