#!/usr/bin/perl -w
use strict;
use POSIX;

my %seen;
while (<*>){
    next unless -f;
    if ($_ =~ /(3g2|3gp|asf|avi|bmp|divx|flv|gif|gvp|jpg|jpe|jpeg|m1v|m4v|mov|mp4|mpa|mpeg|mpe|mpg|nef|ogv|png|ram|rm|swf|tif|viv|wav|wmv)$/i ) {
    # get modify date from file
    my $mdate = strftime "%Y_%m_%d_%H_%M_%S", localtime((lstat($_))[9]);

    # set $was = filename
    my $was = $_;

    # lowercase
    $_ =~ tr/A-Z/a-z/;

    # brackets removal
    $_ =~ s/(\)|\()//g;
    $_ =~ s/(\]|\[)//g;

    # remove whitespace
    $_ =~ s/\s+//g;

    # remove leading _
    $_ =~ s/^_//;

    # remove commas
    $_ =~ s/,//g;

    # remove plus
    $_ =~ s/\+//g;

    # remove amdpersand
    $_ =~ s/\&//g;

    # separator
    $_ = "_" . $_;

    # cull file extention from filename
    #my $ext = ($_ =~ m/([^.]+)$/)[0];

    # search and replace original filename with mdate and original filename
    s/$_/$mdate$_/;

    # already renamed
    #next if $was =~ $mdate && print "hit\t$was\t$mdate\n";
    next if $was =~ $mdate;

    # push previous filename into array keyed on current filename
    $seen{$_} = $was;
    }
}

for my $fn (sort keys %seen){
#    print "$fn\n";
     rename $seen{$fn}, $fn;
}
