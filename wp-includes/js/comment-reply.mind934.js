window.addComment=function(u){var p,v,f,y=u.document,I={commentReplyClass:"comment-reply-link",cancelReplyId:"cancel-comment-reply-link",commentFormId:"commentform",temporaryFormId:"wp-temp-form-div",parentIdFieldId:"comment_parent",postIdFieldId:"comment_post_ID"},e=u.MutationObserver||u.WebKitMutationObserver||u.MozMutationObserver,o="querySelector"in y&&"addEventListener"in u,n=!!y.documentElement.dataset;function t(){r(),e&&new e(d).observe(y.body,{childList:!0,subTree:!0})}function r(e){if(o&&(p=h(I.cancelReplyId),v=h(I.commentFormId),p)){p.addEventListener("touchstart",i),p.addEventListener("click",i);for(var t,n=function(e){var t=I.commentReplyClass;e&&e.childNodes||(e=y);t=y.getElementsByClassName?e.getElementsByClassName(t):e.querySelectorAll("."+t);return t}(e),r=0,d=n.length;r<d;r++)(t=n[r]).addEventListener("touchstart",a),t.addEventListener("click",a)}}function i(e){var t=h(I.temporaryFormId);t&&f&&(h(I.parentIdFieldId).value="0",t.parentNode.replaceChild(f,t),this.style.display="none",e.preventDefault())}function a(e){var t=this,n=l(t,"belowelement"),r=l(t,"commentid"),d=l(t,"respondelement"),t=l(t,"postid");n&&r&&d&&t&&!1===u.addComment.moveForm(n,r,d,t)&&e.preventDefault()}function d(e){for(var t=e.length;t--;)if(e[t].addedNodes.length)return void r()}function l(e,t){return n?e.dataset[t]:e.getAttribute("data-"+t)}function h(e){return y.getElementById(e)}return o&&"loading"!==y.readyState?t():o&&u.addEventListener("DOMContentLoaded",t,!1),{init:r,moveForm:function(e,t,n,r){var d=h(e);f=h(n);var o,i,a,l,m=h(I.parentIdFieldId),s=h(I.postIdFieldId);if(d&&f&&m){l=f,e=I.temporaryFormId,(n=h(e))||((n=y.createElement("div")).id=e,n.style.display="none",l.parentNode.insertBefore(n,l)),r&&s&&(s.value=r),m.value=t,p.style.display="",d.parentNode.insertBefore(f,d.nextSibling),p.onclick=function(){return!1};try{for(var c=0;c<v.elements.length;c++)if(o=v.elements[c],i=!1,"getComputedStyle"in u?a=u.getComputedStyle(o):y.documentElement.currentStyle&&(a=o.currentStyle),(o.offsetWidth<=0&&o.offsetHeight<=0||"hidden"===a.visibility)&&(i=!0),"hidden"!==o.type&&!o.disabled&&!i){o.focus();break}}catch(e){}return!1}}}}(window);