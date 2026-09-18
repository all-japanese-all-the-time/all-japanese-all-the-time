/**
 * Harvey, A Second Face for Your Application's JavaScript
 *
 * Copyright 2012, Joschka Kintscher
 * Released under the MIT License
 *
 * https://github.com/harvesthq/harvey/
 */
(function(){var State,_mediaQueryList;this.Harvey=(function(){function Harvey(){}
Harvey.states={};Harvey.attach=function(mediaQuery,callbacks){var state;if(!this.states.hasOwnProperty(mediaQuery)){this.states[mediaQuery]=[];this._add_css_for(mediaQuery);}
state=new State(mediaQuery,callbacks!=null?callbacks.setup:void 0,callbacks!=null?callbacks.on:void 0,callbacks!=null?callbacks.off:void 0);if(!this.states[mediaQuery].length){this._watch_query(mediaQuery);}
this.states[mediaQuery].push(state);if(this._window_matchmedia(mediaQuery).matches){this._update_states([state],true);}
return state;};Harvey.detach=function(state){var i,s,_i,_len,_ref,_results;_ref=this.states[state.condition];_results=[];for(i=_i=0,_len=_ref.length;_i<_len;i=++_i){s=_ref[i];if(state===s){_results.push(this.states[s.condition][i]=void 0);}else{_results.push(void 0);}}
return _results;};Harvey._watch_query=function(mediaQuery){var _this=this;return this._window_matchmedia(mediaQuery).addListener(function(mql){return _this._update_states(_this.states[mediaQuery],mql.matches);});};Harvey._update_states=function(states,active){var state,_i,_len,_results;_results=[];for(_i=0,_len=states.length;_i<_len;_i++){state=states[_i];if(active){_results.push(state.activate());}else{_results.push(state.deactivate());}}
return _results;};Harvey._mediaList={};Harvey._window_matchmedia=function(mediaQuery){if(window.matchMedia){if(!(mediaQuery in this._mediaList)){this._mediaList[mediaQuery]=window.matchMedia(mediaQuery);}
return this._mediaList[mediaQuery];}
if(!this._listening){this._listen();}
if(!(mediaQuery in this._mediaList)){this._mediaList[mediaQuery]=new _mediaQueryList(mediaQuery);}
return this._mediaList[mediaQuery];};Harvey._listen=function(){var evt,_this=this;evt=window.addEventListener||window.attachEvent;evt('resize',function(){var mediaList,mediaQuery,_ref,_results;_ref=_this._mediaList;_results=[];for(mediaQuery in _ref){mediaList=_ref[mediaQuery];_results.push(mediaList._process());}
return _results;});evt('orientationChange',function(){var mediaList,mediaQuery,_ref,_results;_ref=_this._mediaList;_results=[];for(mediaQuery in _ref){mediaList=_ref[mediaQuery];_results.push(mediaList._process());}
return _results;});return this._listening=true;};Harvey._add_css_for=function(mediaQuery){if(!this.style){this.style=document.createElement('style');this.style.setAttribute('type','text/css');document.getElementsByTagName('head')[0].appendChild(this.style);}
mediaQuery="@media "+mediaQuery+" {.harvey-test{}}";if(!this.style.styleSheet){return this.style.appendChild(document.createTextNode(mediaQuery));}};return Harvey;})();State=(function(){State.prototype.active=false;State.prototype.is_setup=false;function State(condition,setup,on,off){this.condition=condition;this.setup=setup;this.on=on;this.off=off;}
State.prototype.activate=function(){if(this.active){return;}
if(!this.is_setup){if(typeof this.setup==="function"){this.setup();}
this.is_setup=true;}
if(typeof this.on==="function"){this.on();}
return this.active=true;};State.prototype.deactivate=function(){if(!this.active){return;}
if(typeof this.off==="function"){this.off();}
return this.active=false;};return State;})();_mediaQueryList=(function(){function _mediaQueryList(media){this.media=media;this._listeners=[];this.matches=this._matches();}
_mediaQueryList.prototype.addListener=function(listener){this._listeners.push(listener);return void 0;};_mediaQueryList.prototype._process=function(){var callback,current,_i,_len,_ref,_results;current=this._matches();if(this.matches===current){return;}
this.matches=current;_ref=this._listeners;_results=[];for(_i=0,_len=_ref.length;_i<_len;_i++){callback=_ref[_i];_results.push(callback(this));}
return _results;};_mediaQueryList.prototype._matches=function(){if(!this._tester){this._get_tester();}
this._tester.innerHTML='&shy;<style media="'+this.media+'">#harvey-mq-test{width:42px;}</style>';this._tester.removeChild(this._tester.firstChild);return this._tester.offsetWidth===42;};_mediaQueryList.prototype._get_tester=function(){this._tester=document.getElementById('harvey-mq-test');if(!this._tester){return this._build_tester();}};_mediaQueryList.prototype._build_tester=function(){this._tester=document.createElement('div');this._tester.id='harvey-mq-test';this._tester.style.cssText='position:absolute;top:-100em';return document.body.insertBefore(this._tester,document.body.firstChild);};return _mediaQueryList;})();}).call(this);