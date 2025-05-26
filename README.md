all_mtime
=========

A perl script to rename image files based on unix mtime.

usage: ./all_mtime.pl


all_mtime operates on the following file suffixes:

<ul>
<li>3g2</li>
<li>3gp</li>
<li>asf</li>
<li>avi</li>
<li>bmp</li>
<li>divx</li>
<li>flv</li>
<li>gif</li>
<li>gvp</li>
<li>jpg</li>
<li>jpe</li>
<li>jpeg</li>
<li>m1v</li>
<li>m4v</li>
<li>mov</li>
<li>mp4</li>
<li>mpa</li>
<li>mpeg</li>
<li>mpe</li>
<li>mpg</li>
<li>nef</li>
<li>ogv</li>
<li>png</li>
<li>ram</li>
<li>rm</li>
<li>swf</li>
<li>tif</li>
<li>viv</li>
<li>wav</li>
<li>webm</li>
<li>webp</li>
<li>wmv</li>
</ul>


All_mtime strips the following characters from a filename:

()[]&,+

leading _ and whitespace is also removed.


Example:

	example.gif

becomes:

	2014_01_01_15_34_54_example.gif
