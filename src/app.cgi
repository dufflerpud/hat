#!/usr/bin/perl
#
#indx#	app.cgi - A web application to pick names out of a hat
#@HDR@	$Id$
#@HDR@
#@HDR@	Copyright (c) 2024-2026 Christopher Caldwell (Christopher.M.Caldwell0@gmail.com)
#@HDR@
#@HDR@	Permission is hereby granted, free of charge, to any person
#@HDR@	obtaining a copy of this software and associated documentation
#@HDR@	files (the "Software"), to deal in the Software without
#@HDR@	restriction, including without limitation the rights to use,
#@HDR@	copy, modify, merge, publish, distribute, sublicense, and/or
#@HDR@	sell copies of the Software, and to permit persons to whom
#@HDR@	the Software is furnished to do so, subject to the following
#@HDR@	conditions:
#@HDR@	
#@HDR@	The above copyright notice and this permission notice shall be
#@HDR@	included in all copies or substantial portions of the Software.
#@HDR@	
#@HDR@	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
#@HDR@	KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
#@HDR@	WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE
#@HDR@	AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#@HDR@	HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#@HDR@	WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#@HDR@	FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#@HDR@	OTHER DEALINGS IN THE SOFTWARE.
#
#hist#	2026-10-04 - Christopher.M.Caldwell0@gmail.com - Header added
#hist#	2005-02-12 - c.m.caldwell@alumni.unh.edu - Created
########################################################################
#doc#	A web application to pick names out of a hat
########################################################################

use strict;
use lib "/usr/local/lib/perl";
use cpi_setup qw(setup);
use cpi_compress_integer qw(compress_integer);
use cpi_user qw(can_cgroup group_to_name groups groups_of_user
    in_group invite logout_select name_to_group users_in_group);
use cpi_translate qw(trans xlate xprint);
use cpi_db qw(dbadd dbarr dbdel dbget dbpop dbput dbread dbwrite);
use cpi_file qw(cleanup fatal read_file);

&setup(stderr=>"hat");

my $PRODUCT = "Party Hat";
my $DAEMON_SENDER = "C.M.Caldwell\@alumni.UNH.EDU";

my $DEBUG = 0;

my $GROUP;
my $MODE;

our %SEP		= ("REC"=>"-SEP0-","FIELD"=>"-SEP1-","DATA"=>"-SEP2-");

### When not debugging mail set DEBUG_MAIL to nothing ("")
### Otherwise, set it to where mail should go instead of specified dest
my $DEBUG_MAIL = $DAEMON_SENDER;
#$DEBUG_MAIL = "";

my $HAT_USERS		= "$cpi_vars::BASEDIR/lib/hat_users.js";

#########################################################################
#	Print out all known users so user can select his data.		#
#########################################################################
sub userpage
    {
    my $user;
    &xprint(<<EOF);
<title>Who are you?</title>
<body $cpi_vars::BODY_TAGS>
<center><table border=1><tr><td>
<table border=0 cellspacing=1 cellpadding=1>
<tr><th bgcolor=#d0d0d0><font color=white>Select User</font></th></tr>
EOF
    foreach $user ( &users_in_group() )
        {
	&xprint(
	    "<tr><td><a href=$cpi_vars::THIS?user=$user>$user</a></td></tr>\n");
	}
    &xprint("</table></table></center>\n");
    &cleanup(0);
    }

my %matchup = ();
#########################################################################
#	Recursion to put together a random "chain" of who's gifting who	#
#########################################################################
sub recurse
    {
    my( $pickerp, $pickedp ) = @_;
    my $numleft = scalar( @{$pickerp} );
    my @pickerlist = @{$pickerp};
    my $picker = shift( @pickerlist );
    my %excludelist = ();
    my $ind;
    grep( $excludelist{$_}++, &dbget($cpi_vars::DB,$GROUP,$picker,"exclude") );
    my @left_to_try = @{$pickedp};
    while( @left_to_try )
        {
	my $ind = ( ($numleft<=1) ? 0 : int(rand()*scalar(@left_to_try)) );
	my $picked = $left_to_try[ $ind ];
	@left_to_try = grep( $_ ne $picked, @left_to_try );
	if( ($picked ne $picker) && ! $excludelist{$picked} )
	    {
	    $matchup{$picker} = $picked;
	    return 1 if( $numleft <= 1 );
	    my @pickedlist = grep( $_ ne $picked, @{$pickedp} );
	    return 1 if( &recurse( \@pickerlist, \@pickedlist ) );
	    }
	}
    return 0;
    }

#########################################################################
#	Print footer (dependent on privileges).				#
#########################################################################
sub footer()
    {
    my( $mode ) = @_;
    $mode ||= "admin";

    my $href = "$cpi_vars::THIS?SID=$cpi_vars::SID&USER=$cpi_vars::USER";
    my $c = ( ( $GROUP eq "") ? "#d0e0ff" : "#d0d0d0" );
    my $toprint = "<p><center><table width=60% border=4><tr>";
    my( @grouplist ) = 
        (
	&can_cgroup()
	? &groups()
	: &groups_of_user($cpi_vars::USER)
	);
    my $g;
    $toprint .= "<th><select name=GROUP onChange='window.location=\"$href&GROUP=\"+this.value;'><option value=\"\">XL(Select group)\n";
    foreach $g ( @grouplist )
        {
	$toprint .= "<option value=$g" .($g eq $GROUP ?" selected":"") . ">"
	    . &group_to_name($g) . "\n"
	    if( ! grep( $g =~ /$_/,
		"^can_", "^create_", "^tf_", "admin", "user" ) );
	}
    $toprint .= "</select></th>";
    my @buttons = ();
    push( @buttons, "user:XL(User page)" );
    push( @buttons,
	"messages:XL(Messages)",
	"hat_users:XL(Hat administration)" ) if( $cpi_vars::USER eq "chris" );
    foreach my $button ( @buttons )
        {
	my( $butdest, $buttext ) = split(/:/,$button);
	$toprint .= "<th><input type=button onClick='window.location=\"$href&GROUP=$GROUP&func=$butdest\";'"
	    . ( ($butdest eq $mode) ? " style='background-color:cyan'" : "" )
	    . " value=\"$buttext\"></th>";
	}
    $toprint .= "<th><input type=button value=\"XL(Help)\" ";
    $toprint .= "onClick='open(\"$href&func=help\",\"help\",\"toolbar=0,location=0,directories=0,status=0,menubar=0\");'></th>";
    $toprint .= "<th>" . &logout_select() . "</th>";
    $toprint .= "</tr></table></center>";
    &xprint( $toprint );
    &cleanup(0);
    }

#########################################################################
#	Print users in traditional order (sort last name first).	#
#########################################################################
sub sort_user
    {
    my ( $t, $i );

    my @name0=split(/\s+/,
        &dbget($cpi_vars::ACCOUNTDB,"users",$_[0],"fullname"));
    unshift(@name0,pop(@name0));

    my @name1=split(/\s+/,
        &dbget($cpi_vars::ACCOUNTDB,"users",$_[1],"fullname"));
    unshift(@name1,pop(@name1));

    for( $i=0; $name0[$i] || $name1[$i]; $i++ )
        {
	$t = ( $name0[$i] cmp $name1[$i] );
	return $t if( $t );
	}
    return ( $_[0] cmp $_[1] );
    }

#########################################################################
#       Get a list of users for this group (must be able to run hat).   #
#########################################################################
sub viable_users_in_group
    {
    return
        sort {&sort_user($a,$b)}
            grep( &in_group( $_, "can_run_$cpi_vars::PROG" ),
                &users_in_group( $GROUP ) );
    }

#########################################################################
#	Show the primary screen.					#
#########################################################################
sub draw_screen
    {
    my @users = &viable_users_in_group();
    my $nusers = scalar(@users);
    
    my $update_message = "Update [[$GROUP]] database";

    srand( time() );
    my $has_solution = &recurse( \@users, \@users );
    $cpi_vars::FORM{seed} = &dbget($cpi_vars::DB,$GROUP,"SEED");

    my $toprint = <<EOF;
<script>
function send_mail()
    {
    with( window.document.form )
        {
	seed.value = prompt("XL(Enter seed):", seed.value);
	if( isNaN( parseInt(seed.value) ) )
	    {
	    seed.value = Math.floor( Math.random() * 1000000 );
	    }
	func.value = "Selection_Mail";
	submit();
	}
    }
</script>
<body $cpi_vars::BODY_TAGS>
<form name=form method=post>
<input type=hidden name=SID value=$cpi_vars::FORM{SID}>
<input type=hidden name=GROUP value=$GROUP>
<input type=hidden name=MODE value=$MODE>
<input type=hidden name=USER value=$cpi_vars::USER>
<input type=hidden name=func value=Update>
<input type=hidden name=seed value="$cpi_vars::FORM{seed}">
<center><table border=1 $cpi_vars::TABLE_TAGS>
<tr><th rowspan=2>XL(Person)</th>
<th colspan=$nusers>XL(Who to exclude)</th>
EOF
    $toprint .= ("<th rowspan=2>XL(Picked)</th>") if( $DEBUG && $has_solution );
    $toprint .= ("</tr>\n<tr>");
    my( $e );
    foreach $e ( @users )
        {
	$toprint .= ( "<th>" .
	    &dbget($cpi_vars::ACCOUNTDB,"users",$e,"fullname")
	    . "</th>" );
	}
    $toprint .= ("</tr>");
    foreach $e ( @users )
        {
	next if( $MODE eq "user" && ( $cpi_vars::USER ne $e ) );
	$toprint .= ( "<tr><th align=left>".
	    &dbget($cpi_vars::ACCOUNTDB,"users",$e,"fullname")
	    . "</th>" );
	my %ck = ( $e => " checked" );
	grep( $ck{$_}=" checked", &dbget($cpi_vars::DB,$GROUP,$e,"exclude") );
	#my ( $i, $e1 );
	foreach my $e1 ( @users )
	    {
	    $toprint .= ("<td><input type=checkbox$ck{$e1} name=\"exclude_$e\" value=$e1"
	    	. ( $e eq $e1 ? " disabled" : "" )
		. "></td>" );
	    }
	if( $DEBUG && $has_solution)
	    {
	    $_ = &dbget( $cpi_vars::ACCOUNTDB,"users", $matchup{$e}, "fullname" );
	    $toprint .= ("<td>$_</td>");
	    }
	$toprint .= ("</tr>\n");
	}
    my $cols = $nusers + 2;
    $cols++ if( $DEBUG );
    $toprint .= ("<tr><th colspan=$cols>");
    $toprint .= ("<center><table border=0>");
    my ( $subj, $msg, $inv_subj, $inv_msg );
    if( $MODE eq "user" )
        {
	$msg = &trans(
	    &dbget( $cpi_vars::DB, $GROUP, $cpi_vars::USER, "message" ) );
	$toprint .= ("<tr><th valign=top align=right>XL(Message for Secret Santa):</th><td>");
	$toprint .= ("<textarea name=MESSAGE rows=10 cols=78>$msg"
	    . "</textarea></th></tr>");
	if(my $giveto=&dbget($cpi_vars::DB,$GROUP,$cpi_vars::USER,"giveto"))
	    {
	    $update_message .= " and send e-mail";
	    my $gname = 
		&dbget( $cpi_vars::ACCOUNTDB, "users", $giveto, "fullname" );
	    my $tx = &trans(
		&dbget( $cpi_vars::DB, $GROUP, $giveto, "message" ) );
	    $tx =~ s+(http://[^\s]*)+<a href=$1 target=_new_>$1</a>+gs;
	    $toprint .= (<<EOF) if( $tx );
<tr><th valign=top align=right>${gname}'s XL(Message):</th>
    <td><pre>$tx</pre></td></tr>
<tr><th valign=top align=right>XL(Message to) ${gname}:
<br>(Try not to give away who you are)
</th>
    <td><textarea name=TORECEIVER rows=10 cols=78></textarea></th></tr>
EOF
	    }
	}
    else
	{
	$inv_subj = &dbget($cpi_vars::DB,$GROUP,"INVITE_SUBJECT");
	$inv_msg = &dbget($cpi_vars::DB,$GROUP,"INVITE_MESSAGE");
	$toprint .= ("<tr><th align=left>XL(Invitation subject):</th><td>");
	$inv_subj ||= "$cpi_vars::FULLNAME is having a party!";
	$inv_subj = &trans( $inv_subj );
	$toprint .= ("<input type=text name=INVITE_SUBJECT value=\"$inv_subj\" size=80>" .
	    "</td><th>XL(Variables)</th></tr>" .
	    "<tr><th valign=top align=left>XL(Message):</th><td>");
	$inv_msg ||= <<EOF;	# CMC Translation problem
Dear GIVER_FIRST,

$cpi_vars::FULLNAME is inviting you to a party.

For more information, go to URL .
There, you can specify what people you don't want to get a present for
(such as spouses) and leave a message for whomever picks you (such as
your allergies or your color preferences).
EOF
	$inv_msg = &trans( $inv_msg );
	$toprint .= ("<textarea name=INVITE_MESSAGE rows=10 cols=78>$inv_msg</textarea>" .
	    "</td><td valign=top>");
	foreach $_ ("GIVER_FULL","GIVER_FIRST","URL" )
	    { $toprint .= ("$_<br>\n"); }
	$toprint .= ("</td></tr>");
	$subj = &dbget($cpi_vars::DB,$GROUP,"SUBJECT");
	$msg = &dbget($cpi_vars::DB,$GROUP,"MESSAGE");
	$toprint .= ("<tr><th align=left>XL(Selection subject):</th><td>");
	$subj ||= "Your pick from the virtual hat";
	$subj = &trans( $subj );
	$toprint .= ("<input type=text name=SUBJECT value=\"$subj\" size=80>" .
	    "</td><th>XL(Variables)</th></tr>" .
	    "<tr><th valign=top align=left>XL(Message):</th><td>");
	$msg ||= <<EOF;		# CMC Translation problem
Dear GIVER_FIRST,

Your pick from the virtual hat is RECEIVER_FULL.
That is, please get a gift for RECEIVER_FIRST for our Christmas exchange.

Yes, this is the output of a program, but if you have any questions, you
can reply and I (Chris) will see the message.
EOF
	$msg = &trans( $msg );
	$toprint .= ("<textarea name=MESSAGE rows=10 cols=78>$msg</textarea></td>" .
	    "<td valign=top>");
	foreach $_ ("GIVER_FULL","GIVER_FIRST","RECEIVER_FULL", "RECEIVER_FIRST" )
	    { $toprint .= ( "$_<br>\n" ); }
	$toprint .= ("</td></tr>");
	}
    $toprint .= ("</table></center>");
    $toprint .= ("<input type=submit name=Update value=\"XL($update_message)\">");
    $toprint .= ("<input type=button onClick='open(\"$cpi_vars::THIS?func=help\",\"help\",\"toolbar=0,location=0,directories=0,status=0,menubar=0\");' value=\"XL(Help)\">");
    if( $MODE ne "user" )
	{
	$toprint .= ("<input type=submit name=Invitation value=\"XL(Send invitation)\">");
	my @problems = ();
	push(@problems,"XL(Cannot send mail with current restrictions.)")
	    if( ! $has_solution );
	push(@problems,"XL(Mail must have subject.)") if( ! $subj );
	push(@problems,"XL(Mail must have message.)") if( ! $msg );
	if( ! @problems )
	    {
	    $toprint .= ("<input type=submit name=Update onClick='send_mail();' " .
	    	"value=\"XL(Send selection)\">");
	    }
	else
	    {
	    $toprint .= ( "<button disabled><table>" );
	    $toprint .= ( "<tr><th><font color=red>XL(Cannot send mail because):</th>\n" );
	    $toprint .= ( "<td><font color=red>" );
	    $toprint .= ( join("<br>\n",@problems) );
	    $toprint .= ( "</td></tr></table></button>\n" );
	    }
	}
    $toprint .= ("</th></tr></table></form></center>\n");
    &xprint( $toprint );
    &footer( $MODE );
    &cleanup(0);
    }

#########################################################################
#	Update the database with the results of the primary form.	#
#########################################################################
sub do_update
    {
    #&print_form("Update called");
    if( $MODE eq "user" )
        {
	my @users = &viable_users_in_group();

	my @ilist = split(/,/,$cpi_vars::FORM{"exclude_$cpi_vars::USER"});
	my $lastmessage= &dbget($cpi_vars::DB,$GROUP,$cpi_vars::USER,"message");
	my $lang = ( $cpi_vars::LANG || "en" );
	my $last_translated_message = &trans( $lastmessage );
	$last_translated_message = $1
	    if( $last_translated_message =~ /{[a-z]+?--(.*)}$/s );
	if( $cpi_vars::FORM{MESSAGE} ne $last_translated_message )
	    {
	    &dbwrite( $cpi_vars::DB );
	    &dbput($cpi_vars::DB,$GROUP,$cpi_vars::USER,"exclude",
		&dbarr(@ilist));
	    &dbput($cpi_vars::DB,$GROUP,$cpi_vars::USER,"message",
		"$lang|$cpi_vars::FORM{MESSAGE}")
		    if( $cpi_vars::FORM{MESSAGE} ne $last_translated_message );
	    if( $cpi_vars::FORM{MESSAGE} )
		{
		my $giver = &dbget($cpi_vars::DB,$GROUP,$cpi_vars::USER,"getfrom");
		if( ! $giver )
		    { &xprint("XL(Message updated but there is no Secret Santa to send to yet.)"); }
		else
		    {
		    my $email = &dbget($cpi_vars::ACCOUNTDB,"users",$giver,"email");
		    my $destaddr = ( $DEBUG_MAIL ? $DEBUG_MAIL : $email );
		    my $gfull = &dbget($cpi_vars::ACCOUNTDB,"users",$giver,"fullname");
		    open( MAIL, "| $cpi_vars::SENDMAIL -f $DAEMON_SENDER $destaddr" ) ||
			&fatal("Cannot send mail to Giver:  $!");
		    my $msg = join("\n\t",split(/\n/,$cpi_vars::FORM{MESSAGE}));
		    my $fname = &dbget($cpi_vars::ACCOUNTDB,"users",
		        $cpi_vars::USER,"fullname");
		    print MAIL <<EOF;
From:  $DAEMON_SENDER
To:  $gfull <$email>
Subject:  ${fname}'s wish list

${fname}'s wish list:
	$msg
EOF
		    close( MAIL );
		    &xprint("XL(Message sent to your Secret Santa.)<br>\n");
		    }
		}
	    &dbpop( $cpi_vars::DB );
	    }
	if( $cpi_vars::FORM{TORECEIVER} =~ /[^\s]/s )
	    {
	    my $giveto = &dbget($cpi_vars::DB,$GROUP,$cpi_vars::USER,"giveto");
	    if( $giveto )
		{
		my $email = &dbget($cpi_vars::ACCOUNTDB,"users",$giveto,"email");
		my $destaddr = ( $DEBUG_MAIL ? $DEBUG_MAIL : $email );
		my $gfull = &dbget($cpi_vars::ACCOUNTDB,"users",$giveto,"fullname");
		open( MAIL, "| $cpi_vars::SENDMAIL -f $DAEMON_SENDER $destaddr" ) ||
		    &fatal("Cannot send mail to Giver:  $!");
		my $msg = join("\n\t",split(/\n/,$cpi_vars::FORM{TORECEIVER}));
		print MAIL <<EOF;
From:  $DAEMON_SENDER
To:  $gfull <$email>
Subject:  A message from your Secret Santa:

Your Secret Santa writes:
	$msg
EOF
		close( MAIL );
		&xprint("XL(Message sent to) $email.<br>\n");
		}
	    }
	}
    else
	{
	my @inds = ();
	foreach $_ ( keys %cpi_vars::FORM )
	    {
	    push( @inds, $1 ) if( /email_(.*)/ );
	    }
	my $ind;
	my @elist = ();
	my %transtext;
	my @translist=("SUBJECT","MESSAGE","INVITE_SUBJECT","INVITE_MESSAGE");
	my $tx;
	foreach $tx ( @translist )
	    {
	    $transtext{$tx} = &trans(
	        &dbget($cpi_vars::DB,$GROUP,$tx) );
	    }
	&dbwrite( $cpi_vars::DB );
	foreach $ind ( @inds )
	    {
	    my @ilist = split(/,/,$cpi_vars::FORM{"exclude_$ind"});
	    &dbput($cpi_vars::DB,$GROUP,$ind,"exclude",
		&dbarr(@ilist));
	    push( @elist, $ind );
	    }
	foreach $tx ( @translist )
	    {
	    &dbput($cpi_vars::DB,$GROUP,$tx,
		"$cpi_vars::LANG|$cpi_vars::FORM{$tx}")
		if( $cpi_vars::FORM{$tx} ne $transtext{$tx} );
	    }
	&dbpop( $cpi_vars::DB );
	}
    }

#########################################################################
#	Put together custom e-mail for each giver indicating target.	#
#########################################################################
sub send_selection
    {
    &do_update();
    my @users = &viable_users_in_group();
    my $giver;
    srand( $cpi_vars::FORM{seed} );
    &recurse( \@users, \@users ) || &fatal("No solution for configuration");
    &dbwrite( $cpi_vars::DB );
    &dbput( $cpi_vars::DB, $GROUP, "SEED", $cpi_vars::FORM{seed} );
    foreach $giver ( @users )
        {
	my $receiver = $matchup{$giver};
        &dbput( $cpi_vars::DB, $GROUP, $giver, "giveto", $receiver );
        &dbput( $cpi_vars::DB, $GROUP, $receiver, "getfrom", $giver );
	}
    &dbpop( $cpi_vars::DB );
    foreach $giver ( @users )
        {
	my $receiver = $matchup{$giver};
	my %names =
	    (
	    "GIVER_FULL" =>
		&dbget($cpi_vars::ACCOUNTDB,"users",$giver,"fullname"),
	    "RECEIVER_FULL" =>
		&dbget($cpi_vars::ACCOUNTDB,"users",$receiver,"fullname")
	    );
	my( $k );
	foreach $k ( keys %names )
	    {
	    $_ = $k;
	    s/_FULL/_FIRST/g;
	    $names{$_} = (split(/\s+/,$names{$k}))[0];
	    }
	my %text = ();
	foreach $k ( "SUBJECT", "MESSAGE" )
	    {
	    $text{$k} = &dbget($cpi_vars::DB,$GROUP,$k);
	    $text{$k} =~ s/^[a-z]*\|//;
	    }
	foreach $k ( keys %text )
	    {
	    foreach $_ ( keys %names )
	        { $text{$k} =~ s/$_/$names{$_}/g; }
	    }
	$_ = &dbget($cpi_vars::DB,$GROUP,$receiver,"message");
	s/^[a-z]*\|//;
	$text{MESSAGE} .=
	    "\n$names{RECEIVER_FULL} has the following message:\n$_"
	    if( /\w/ );
	my $destemail = &dbget($cpi_vars::ACCOUNTDB,"users",$giver,"email");
	my $destaddr = ( $DEBUG_MAIL ? $DEBUG_MAIL : $destemail );

	my $srcemail = &dbget($cpi_vars::ACCOUNTDB,"users",$receiver,"email");
	my $srcaddr = ( $DAEMON_SENDER ? ${DAEMON_SENDER} : $srcemail );

	my $srctext =
	    ( $DAEMON_SENDER
	    ? ${DAEMON_SENDER}
	    : "$names{RECEIVER_FULL} <$srcaddr>"
	    );

	open( MAIL, "| $cpi_vars::SENDMAIL -f $srcaddr $destaddr" ) ||
	    &fatal("Cannot send mail to $giver:  $!");
	print MAIL <<EOF;
From:  $srctext
To:  $names{GIVER_FULL} <$giver>
Subject:  $text{SUBJECT}

$text{MESSAGE}
EOF
	close( MAIL );
	$_ = "XL(Gift destination sent to) <b><u><i>$names{GIVER_FULL}</i></u></b> XL(via) <b><i><u>$destemail</u></i></b>";
	#$_ .= " XL(for) <b><i><u>$names{RECEIVER_FULL}</u></i></b>";
	$_ .= ".<br>\n";
	&xprint( $_ );
	}
    &xprint(<<EOF);
<form method=post>
<input type=hidden name=SID value=$cpi_vars::FORM{SID}>
<input type=hidden name=USER value=$cpi_vars::USER>
<input type=hidden name=MODE value=$MODE>
<input type=hidden name=GROUP value="$GROUP">
XL(The seed for this mail is) $cpi_vars::FORM{seed}.<br>
<input type=submit value="XL(Continue)">
</form>
EOF
    }

#########################################################################
#	Put together custom e-mail indicating a party has been setup.	#
#########################################################################
sub send_invite
    {
    &do_update();
    my @users = &viable_users_in_group();
    my %sids = ();
    my $giver;
    foreach $giver ( @users )
        {
	$sids{$giver} = &compress_integer( rand() );
	#$sids{$giver} = &dbget($cpi_vars::DB,$GROUP,$giver,"SID");
	my %names =
	    (
	    "GIVER_FULL" => &dbget($cpi_vars::ACCOUNTDB,"users",$giver,"fullname"),
	    );
	my( $k );
	foreach $k ( keys %names )
	    {
	    $_ = $k;
	    s/_FULL/_FIRST/g;
	    $names{$_} = (split(/\s+/,$names{$k}))[0];
	    }
	my %text = ();
	foreach $k ( "INVITE_SUBJECT", "INVITE_MESSAGE" )
	    {
	    $text{$k} = &dbget($cpi_vars::DB,$GROUP,$k);
	    $text{$k} =~ s/^[a-z]*\|//;
	    }

	$names{URL}	= $cpi_vars::URL;
	$names{URL}	=~ s+//127\.0\.0\.1:80/+//www.brightsands.com:80/+;

	$names{URL} =~ s/\?.*//;
	$names{URL}.="?GROUP=$GROUP&ATTENDEE=$giver&SID=$sids{$giver}";
	foreach $k ( keys %text )
	    {
	    foreach $_ ( keys %names )
	        { $text{$k} =~ s/$_/$names{$_}/g; }
	    }
	my $destemail = &dbget($cpi_vars::ACCOUNTDB,"users",$giver,"email");
	my $destaddr = ( $DEBUG_MAIL ? $DEBUG_MAIL : $destemail );

	#my $srcemail = &dbget($cpi_vars::ACCOUNTDB,"users",$receiver,"email");
	#my $srcaddr = ( $DAEMON_SENDER ? ${DAEMON_SENDER} : $srcemail );
	my $srcaddr = $DAEMON_SENDER;
	my $srctext =
	    ( $DAEMON_SENDER
	    ? $DAEMON_SENDER
	    : "$names{RECEIVER_FULL} <$srcaddr>"
	    );

	open( MAIL, "| $cpi_vars::SENDMAIL -f $srcaddr $destaddr" ) ||
	    &fatal("Cannot send mail to $giver:  $!");
	print MAIL <<EOF;
From:  $srctext
To:  $names{GIVER_FULL} <$giver>
Subject:  $text{INVITE_SUBJECT}

$text{INVITE_MESSAGE}
EOF
	close( MAIL );
	&xprint("XL(Invitation sent to) <b><u><i>$names{GIVER_FULL}</i></u></b> XL(via) <b><u><i>$destemail</i></u></b>.<br>\n");
	}
    &dbwrite( $cpi_vars::DB );
    foreach $giver ( keys %sids )
        {
	&dbput( $cpi_vars::DB, $GROUP, $giver, "SID", $sids{$giver} );
	&dbput( $cpi_vars::DB, $GROUP, $giver, "giveto", "" );
	&dbput( $cpi_vars::DB, $GROUP, $giver, "getfrom", "" );
	}
    &dbpop( $cpi_vars::DB );
    &xprint(<<EOF);
<form method=post>
<input type=hidden name=SID value=$cpi_vars::FORM{SID}>
<input type=hidden name=USER value="$cpi_vars::USER">
<input type=hidden name=GROUP value="$GROUP">
<input type=submit value="XL(Continue)">
</form>
EOF
    }

#########################################################################
#	Print a help message						#
#########################################################################
sub help
    {
    my $ORGANIZER="The party organizer";
    &xprint(<<EOF);
<body $cpi_vars::BODY_TAGS>
XL(Welcome to $cpi_vars::PROG, a program to facilitate people organizing a
"Secret Santa" style party.  For those of you unfamiliar with
how such a party works:
    <ul>
    <li>$ORGANIZER goes to <a href=$cpi_vars::URL>$cpi_vars::URL</a> and logs in with
        an account previously created by the site administrator.
    <li>If the party organizer has the option, he should select party that
        he wishes to administer.
    <li>$ORGANIZER adds party goers with their e-mail addresses.  Note that
        $ORGANIZER does not need to actually be one of the party goers.
    <li>$ORGANIZER hits "Update" for the group database.
    <li>$ORGANIZER then goes through each partygoer and clicks on the
        check box under the partygoers that the user should not end up
	having to select presents for.
    <li>$ORGANIZER then creates a subject header and an invitation message.
        The invitation typically contains the time and location of the party.
	<ul>
	<li>Wherever the text GIVER_FIRST appears, it is replaced by the
	    recipients first name.
	<li>Wherever the text GIVER_FULL appears, it is replaced by the
	    recipients full name.
	<li>Wherever the text URL appears, it is replaced by a URL
	    pointing to the site which will allow the recipient to modify
	    his exclusions and update a message (which might contain what
	    he or she wants to receive, is alergic to, etc).
	</ul>
    <li>$ORGANIZER hits "Update" for the group database.
    <li>$ORGANIZER hits "Send invitation" which will then send e-mail to
        each partygoer.
    </ul>
)
EOF
    &cleanup(0);
    }

#########################################################################
#	userpage handler						#
#########################################################################
sub userpage_handler
    {
    if( $cpi_vars::FORM{func} eq "Update" )
	{ &do_update(); draw_screen(); }
    else
	{ &draw_screen(); }
    }

#########################################################################
#	message handler							#
#########################################################################
sub messagepage_handler
    {
    if( $cpi_vars::FORM{Invitation} )
	{ &send_invite(); }
    elsif( $cpi_vars::FORM{func} eq "Update" )
	{ &do_update(); draw_screen(); }
    elsif( $cpi_vars::FORM{func} eq "Selection_Mail" )
	{ &send_selection(); }
    else
	{ &draw_screen(); }
    }

#########################################################################
#	Cheat - dump who gives to whom.					#
#########################################################################
sub cheat
    {
    my $sep = "";
    &dbread( $cpi_vars::DB );
    foreach my $group ( &groups() )
        {
	my @attendees = &viable_users_in_group();
	if( @attendees )
	    {
	    print $sep, "Group ${group}:\n";
	    $sep = "\n";
	    foreach my $attendee ( @attendees )
	        {
		my $fname = &dbget($cpi_vars::ACCOUNTDB,"users",$attendee,"fullname");
		my $givesto = &dbget($cpi_vars::DB,$group,$attendee,"giveto");
		my $tname = &dbget($cpi_vars::ACCOUNTDB,"users",$givesto,"fullname");
		printf("  %-30s %25s=>%s\n",$attendee,$fname,$tname);
		}
	    } 
	}
    &cleanup(0);
    }

#########################################################################
#	Return true if user can access named hat.			#
#########################################################################
sub in_hat_group
    {
    my( $hat_name, $username ) = @_;
    $username = $cpi_vars::USER if( ! defined( $username ) );
    return 1 if( &in_group($username,"hat_administration") );
    return &in_group( $username, $hat_name );
    }

#########################################################################
#	Add user to a hat group.					#
#########################################################################
sub add_user_to_hat_group
    {
    my( $hat_name, $username ) = @_;
    $username = $cpi_vars::REALUSER if( ! defined( $username ) );
    my $group_name = &name_to_group("tf_$hat_name");
    print "Adding $username to group $hat_name<br>\n";
    &dbwrite($cpi_vars::ACCOUNTDB);
    &dbadd($cpi_vars::ACCOUNTDB,"users",$username,"groups",$group_name);
    &dbpop($cpi_vars::ACCOUNTDB);
    }

#########################################################################
#	Delete user from a hat group.					#
#########################################################################
sub remove_user_from_hat_group
    {
    my( $hat_name, $username ) = @_;
    $username = $cpi_vars::REALUSER if( ! defined( $username ) );
    &dbwrite($cpi_vars::ACCOUNTDB);
    &dbdel($cpi_vars::ACCOUNTDB,"users",$username,"groups",$hat_name);
    &dbpop($cpi_vars::ACCOUNTDB);
    }

#########################################################################
#	Called when user logged in, accepting an invitation.		#
#########################################################################
sub invitation_handler
    {
    my( @args ) = @_;
    my $action;
    while( $action = shift( @args ) )
	{
	if( $action eq "add_to_hat_group" )
	    {
	    my $value = shift(@args);
	    &add_user_to_hat_group( $value );
	    $cpi_vars::FORM{"hat_type"} = $value;
	    }
	elsif( $action eq "add_to_group" )
	    {
	    my $newgroup = shift(@args);
	    &dbwrite( $cpi_vars::ACCOUNTDB );
	    &dbadd( $cpi_vars::ACCOUNTDB, "users", $cpi_vars::REALUSER,
	        "groups", $newgroup );
	    &dbpop( $cpi_vars::ACCOUNTDB );
	    print "Adding $cpi_vars::REALUSER to $newgroup.<br>\n";
	    }
	else
	    {
	    print "Unknown action [$action]<br>\n";
	    last;
	    }
	}
    }

#########################################################################
#	Do substitutions in a javascript template file.			#
#########################################################################
sub template_substitutions
    {
    my( $fn, @varvals ) = @_;
    my $text = &read_file( $fn );
    push( @varvals,
	"BODY_TAGS",	$cpi_vars::BODY_TAGS,
	"TABLE_TAGS",	$cpi_vars::TABLE_TAGS,
	"SID",		$cpi_vars::SID,
	"USER",		$cpi_vars::USER,
	"GROUP",	$GROUP,
	"SEPS",		join(",", map { "${_}:'$SEP{$_}'" } keys %SEP )
	);
    grep( $text =~ s/\b${_}_SEP\b/'$SEP{$_}'/gs, keys %SEP );
    while( my $tvar = shift(@varvals) )
        {
	my $tval = shift(@varvals);
	$text =~ s/%%${tvar}%%/$tval/gs;
	}
    return $text;
    }


#########################################################################
#	Handle invitation page						#
#########################################################################
sub hat_user_page_handler
    {
    my $msg = "";
    my @msgs = ();
    my @problems = ();
    if( $cpi_vars::FORM{func} eq "hat_users_update" )
	{
	if( $cpi_vars::FORM{invitees_vals} )
	    {
	    my @options = ( "add_to_hat_group", $GROUP );
	    foreach my $new_user_stuff
		( split(/$SEP{REC}/,$cpi_vars::FORM{invitees_vals}) )
		{
		my($means,$address) = split( /$SEP{FIELD}/, $new_user_stuff );
		$means = "Email";
		&invite($means,$address,&xlate(<<EOF),@options);
$cpi_vars::USER XL(invites you to join the group [[$GROUP]].)

XL(To do this, click on the following URL and login or create a new
account as necessary):
EOF
		push(@msgs, "XL(Invitation sent via [[$means]] to [[$address]].)");
		}
	    }

        if( $cpi_vars::FORM{delete_users} )
            {
            &dbwrite( $cpi_vars::DB );
            foreach my $u ( split( /,/, $cpi_vars::FORM{delete_users} ) )
                { &remove_user_from_hat_group( $GROUP, $u ); }
            &dbpop( $cpi_vars::DB );
            }

	push( @msgs, (@problems ? @problems : "<b>XL(Update complete.)</b>") );
	}

    my @user_parts;
    foreach my $user ( &viable_users_in_group($GROUP) )
        {
	push( @user_parts,
	    "<tr><th><input type=checkbox name=delete_users value=$user",
	    " onChange='trigger_change(1);'></th><td>",
	    &dbget($cpi_vars::ACCOUNTDB,"users",$user,"fullname"),
	    "</td></tr>" );
	}
    push( @user_parts,
	"<tr><th colspan=2>XL(No users in group [[$GROUP]].)</th></tr>" )
        if( ! @user_parts );

    $msg = "<li>".join("<li>",@msgs) if( @msgs );

    &xprint( &template_substitutions( $HAT_USERS,
	"MSG",			$msg,
	"USER_LIST",		join("",@user_parts)
	) );

    &footer($MODE);
    }

#########################################################################
#	Main								#
#########################################################################
&cheat() if( $ARGV[0] eq "cheat" );

&fatal("XL(Usage):  $cpi_vars::PROG.cgi (cheat|dump|dumpaccounts|dumptranslations|undump|undumpaccounts|undumptranslations) [ dumpname ]")
    if( $ENV{SCRIPT_NAME} eq "" );

$GROUP		= ( $cpi_vars::FORM{GROUP}	|| ""		);
$MODE		= ( $cpi_vars::FORM{MODE}		|| "user"	);

#if( $cpi_vars::USER )
#    {
#    if( $cpi_vars::FORM{func} eq "Update" )
#	{ &do_update(); draw_screen(); }
#    else
#	{ &draw_screen(); }
#    }


$MODE = $cpi_vars::FORM{func}
    if( grep($cpi_vars::FORM{func} eq $_, "userpage","messages","hat_users") );

if( $cpi_vars::FORM{func} eq "help" )		{ &help(); }
elsif( $MODE eq "user" )			{ &userpage_handler(); }
elsif( $MODE eq "messages" )			{ &messagepage_handler(); }
elsif( $MODE eq "hat_users" )			{ &hat_user_page_handler(); }
else
    { &fatal("Unknown mode \"$MODE\"."); }
