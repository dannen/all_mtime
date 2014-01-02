all_mtime
=========

A perl script to rename image files based on unix mtime.

usage: ./all_mtime.pl


all_mtime operates on the following file suffixes:

<ul>
<li>3g2
<li>3gp
<li>asf
<li>avi
<li>bmp
<li>divx
<li>flv
<li>gif
<li>gvp
<li>jpg
<li>jpe
<li>jpeg
<li>m1v
<li>m4v
<li>mov
<li>mp4
<li>mpa
<li>mpeg
<li>mpe
<li>mpg
<li>nef
<li>ogv
<li>png
<li>ram
<li>rm
<li>swf
<li>tif
<li>viv
<li>wav
<li>wmv
</ul>


All_mtime strips the following characters from a filename:

()[]&,+

leading _ and whitespace is also removed.


Example:

	example.gif

becomes:

	2014_01_01_15_34_54_example.gif
