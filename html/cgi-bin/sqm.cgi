#!/usr/bin/perl
###############################################################################
#                                                                             #
# IPFire.org - A linux based firewall                                         #
# SQM (Smart Queue Management) addon                                          #
#                                                                             #
###############################################################################

use strict;

require '/var/ipfire/general-functions.pl';
require "${General::swroot}/lang.pl";
require "${General::swroot}/header.pl";

my $settingsfile = "${General::swroot}/sqm/settings";
my $qossettingsfile = "${General::swroot}/qos/settings";
my $sqmctrl = '/usr/local/bin/sqmctrl';

my %settings = ();
my %qossettings = ();
my %cgiparams = ();
my %checked = ();
my %selected = ();
my $errormessage = '';
my $warnmessage = '';

my %tr = (
	'sqm' => 'SQM',
	'sqm title' => 'Smart Queue Management',
	'sqm help' => 'SQM shapes traffic slightly below the ISP rate using CAKE (or HTB+fq_codel) and an IFB device for download. This is not the same as IPFire Quality of Service (HTB classes on IMQ). Only one of SQM or QoS can own the RED interface.',
	'sqm qos conflict' => 'IPFire Quality of Service is enabled. Stop QoS under Services before starting SQM.',
	'sqm enabled' => 'Enable SQM',
	'sqm interface' => 'Interface',
	'sqm interface hint' => 'Leave empty to use the RED interface from /var/ipfire/red/iface (recommended; follows PPPoE).',
	'sqm download' => 'Download speed (kbit/s)',
	'sqm upload' => 'Upload speed (kbit/s)',
	'sqm rates hint' => 'Use about 85–95% of measured goodput. Set a direction to 0 to disable shaping in that direction.',
	'sqm script' => 'Queue setup script',
	'sqm qdisc' => 'Queueing discipline',
	'sqm link layer' => 'Link layer',
	'sqm overhead' => 'Per-packet overhead (bytes)',
	'sqm mpu' => 'MPU (bytes)',
	'sqm nat' => 'NAT (cake nat)',
	'sqm dual host' => 'Per-host fairness (dual-srchost / dual-dsthost)',
	'sqm wash' => 'Wash DSCP on ingress',
	'sqm ack filter' => 'ACK filter (upload, cake only)',
	'sqm extra ingress' => 'Extra ingress qdisc options',
	'sqm extra egress' => 'Extra egress qdisc options',
	'sqm debug' => 'Debug logging',
	'sqm save' => 'Save',
	'sqm start' => 'Start',
	'sqm stop' => 'Stop',
	'sqm restart' => 'Restart',
	'sqm status' => 'Status',
	'sqm advanced' => 'Advanced',
	'sqm piece of cake' => 'piece_of_cake.qos — CAKE, single tin (recommended)',
	'sqm layer cake' => 'layer_cake.qos — CAKE, DSCP tins (diffserv3)',
	'sqm simple' => 'simple.qos — HTB + fq_codel (lower CPU at high rates; needs nftables)',
	'sqm none' => 'none (no overhead compensation)',
	'sqm ethernet' => 'Ethernet',
	'sqm atm' => 'ATM (DSL)',
	'sqm ptm' => 'PTM (VDSL)',
	'sqm invalid rate' => 'Download and upload must be non-negative integers (kbit/s).',
	'sqm invalid iface' => 'Interface name contains invalid characters.',
	'sqm invalid overhead' => 'Overhead and MPU must be non-negative integers.',
	'sqm saved' => 'Settings saved.',
	'sqm started' => 'SQM started.',
	'sqm stopped' => 'SQM stopped.',
	'sqm start failed' => 'SQM failed to start. Check the system log (tag: sqm).',
);

sub T {
	my $key = shift;
	return $Lang::tr{$key} if defined $Lang::tr{$key} && $Lang::tr{$key} ne $key;
	return $tr{$key} if defined $tr{$key};
	return $key;
}

sub h {
	my $s = shift;
	$s = '' unless defined $s;
	$s =~ s/&/&amp;/g;
	$s =~ s/</&lt;/g;
	$s =~ s/>/&gt;/g;
	$s =~ s/"/&quot;/g;
	$s =~ s/'/&#39;/g;
	return $s;
}

sub defaults {
	my %d = (
		'ENABLED' => 'off',
		'INTERFACE' => '',
		'DOWNLOAD' => '50000',
		'UPLOAD' => '10000',
		'QDISC' => 'cake',
		'SCRIPT' => 'piece_of_cake.qos',
		'LINKLAYER' => 'ethernet',
		'OVERHEAD' => '18',
		'STAB_MPU' => '64',
		'NAT' => 'on',
		'DUAL_HOST' => 'on',
		'WASH' => 'on',
		'ACK_FILTER' => 'off',
		'IQDISC_OPTS' => '',
		'EQDISC_OPTS' => '',
		'SQM_DEBUG' => '0',
	);
	return %d;
}

sub qos_enabled {
	return 0 unless -e $qossettingsfile;
	%qossettings = ();
	&General::readhash($qossettingsfile, \%qossettings) if -f $qossettingsfile;
	return 1 if defined $qossettings{'ENABLED'} && $qossettings{'ENABLED'} eq 'on';
	return 0;
}

sub valid_iface {
	my $if = shift;
	return 1 if $if eq '';
	return $if =~ /^[A-Za-z0-9_.:-]+$/;
}

sub valid_uint {
	my $v = shift;
	return defined $v && $v =~ /^\d+$/;
}

%settings = defaults();
if (-f $settingsfile) {
	&General::readhash($settingsfile, \%settings);
}

&Header::getcgihash(\%cgiparams);

if ($cgiparams{'ACTION'} ne '') {
	foreach my $key (keys %{ { defaults() } }) {
		if (exists $cgiparams{$key}) {
			$settings{$key} = $cgiparams{$key};
		}
	}

	# Checkboxes are omitted when unchecked.
	foreach my $box ('ENABLED', 'NAT', 'DUAL_HOST', 'WASH', 'ACK_FILTER') {
		if ($cgiparams{'ACTION'} eq T('sqm save')
			|| $cgiparams{'ACTION'} eq T('sqm start')
			|| $cgiparams{'ACTION'} eq T('sqm restart')) {
			$settings{$box} = ($cgiparams{$box} eq 'on') ? 'on' : 'off';
		}
	}
	$settings{'SQM_DEBUG'} = ($cgiparams{'SQM_DEBUG'} eq '1' || $cgiparams{'SQM_DEBUG'} eq 'on') ? '1' : '0';

	if ($cgiparams{'ACTION'} eq T('sqm save')
		|| $cgiparams{'ACTION'} eq T('sqm start')
		|| $cgiparams{'ACTION'} eq T('sqm restart')) {

		unless (valid_uint($settings{'DOWNLOAD'}) && valid_uint($settings{'UPLOAD'})) {
			$errormessage = T('sqm invalid rate');
		}
		unless (valid_iface($settings{'INTERFACE'})) {
			$errormessage = T('sqm invalid iface');
		}
		unless (valid_uint($settings{'OVERHEAD'}) && valid_uint($settings{'STAB_MPU'})) {
			$errormessage = T('sqm invalid overhead');
		}
		foreach my $opt ('IQDISC_OPTS', 'EQDISC_OPTS') {
			$settings{$opt} = '' unless defined $settings{$opt};
			unless ($settings{$opt} =~ m/^[A-Za-z0-9_.:+=,\/\s-]*$/) {
				$errormessage = T('sqm invalid iface');
			}
		}
		my %scripts = map { $_ => 1 } (
			'piece_of_cake.qos', 'layer_cake.qos', 'simple.qos'
		);
		$settings{'SCRIPT'} = 'piece_of_cake.qos' unless $scripts{ $settings{'SCRIPT'} };
		my %layers = map { $_ => 1 } ('none', 'ethernet', 'atm', 'ptm');
		$settings{'LINKLAYER'} = 'ethernet' unless $layers{ $settings{'LINKLAYER'} };
		if ($settings{'SCRIPT'} eq 'simple.qos') {
			$settings{'QDISC'} = 'fq_codel';
		} else {
			$settings{'QDISC'} = 'cake';
		}

		# Never write IMQ.
		if ($settings{'INTERFACE'} =~ /^imq/i) {
			$errormessage = T('sqm invalid iface');
		}

		if ($errormessage eq '') {
			if ($cgiparams{'ACTION'} eq T('sqm start') || $cgiparams{'ACTION'} eq T('sqm restart')) {
				$settings{'ENABLED'} = 'on';
			}
			&General::writehash($settingsfile, \%settings);
			$warnmessage = T('sqm saved') if $cgiparams{'ACTION'} eq T('sqm save');
		}
	}

	if ($errormessage eq '') {
		if ($cgiparams{'ACTION'} eq T('sqm start') || $cgiparams{'ACTION'} eq T('sqm restart')) {
			if (qos_enabled()) {
				$errormessage = T('sqm qos conflict');
			} else {
				my $rc = system($sqmctrl, ($cgiparams{'ACTION'} eq T('sqm restart') ? 'restart' : 'start'));
				if ($rc == 0) {
					$warnmessage = T('sqm started');
				} else {
					$errormessage = T('sqm start failed');
				}
			}
		} elsif ($cgiparams{'ACTION'} eq T('sqm stop')) {
			system($sqmctrl, 'stop');
			$settings{'ENABLED'} = 'off';
			&General::writehash($settingsfile, \%settings);
			$warnmessage = T('sqm stopped');
		}
	}
}

if (-f $settingsfile) {
	%settings = defaults();
	&General::readhash($settingsfile, \%settings);
}

$checked{'ENABLED'}{'on'} = ($settings{'ENABLED'} eq 'on') ? "checked='checked'" : '';
$checked{'NAT'}{'on'} = ($settings{'NAT'} eq 'on') ? "checked='checked'" : '';
$checked{'DUAL_HOST'}{'on'} = ($settings{'DUAL_HOST'} eq 'on') ? "checked='checked'" : '';
$checked{'WASH'}{'on'} = ($settings{'WASH'} eq 'on') ? "checked='checked'" : '';
$checked{'ACK_FILTER'}{'on'} = ($settings{'ACK_FILTER'} eq 'on') ? "checked='checked'" : '';
$checked{'SQM_DEBUG'}{'1'} = ($settings{'SQM_DEBUG'} eq '1') ? "checked='checked'" : '';

$selected{'SCRIPT'}{ $settings{'SCRIPT'} } = "selected='selected'";
$selected{'LINKLAYER'}{ $settings{'LINKLAYER'} } = "selected='selected'";

my $qos_on = qos_enabled();

&Header::showhttpheaders();
&Header::openpage(T('sqm title'), 1, '');
&Header::openbigbox('100%', 'left', '');

if ($errormessage) {
	&Header::openbox('100%', 'left', $Lang::tr{'error messages'} || 'Error');
	print "<p class='base'>" . h($errormessage) . "</p>\n";
	&Header::closebox();
}
if ($warnmessage && !$errormessage) {
	&Header::openbox('100%', 'left', $Lang::tr{'notes'} || 'Notice');
	print "<p class='base'>" . h($warnmessage) . "</p>\n";
	&Header::closebox();
}

if ($qos_on) {
	&Header::openbox('100%', 'left', T('sqm qos conflict'));
	print "<p>" . T('sqm qos conflict') . "</p>\n";
	&Header::closebox();
}

&Header::openbox('100%', 'left', T('sqm title'));
print <<END;
<p>@{[ T('sqm help') ]}</p>
<form method='post' action='$ENV{'SCRIPT_NAME'}'>
<table width='100%'>
<tr>
	<td width='40%'><input type='checkbox' name='ENABLED' value='on' $checked{'ENABLED'}{'on'} /> @{[ T('sqm enabled') ]}</td>
	<td width='60%'></td>
</tr>
<tr>
	<td>@{[ T('sqm interface') ]}:</td>
	<td><input type='text' name='INTERFACE' value='@{[ h($settings{'INTERFACE'}) ]}' size='16' />
	<br /><em>@{[ T('sqm interface hint') ]}</em></td>
</tr>
<tr>
	<td>@{[ T('sqm download') ]}:</td>
	<td><input type='text' name='DOWNLOAD' value='@{[ h($settings{'DOWNLOAD'}) ]}' size='10' /></td>
</tr>
<tr>
	<td>@{[ T('sqm upload') ]}:</td>
	<td><input type='text' name='UPLOAD' value='@{[ h($settings{'UPLOAD'}) ]}' size='10' /></td>
</tr>
<tr><td colspan='2'><em>@{[ T('sqm rates hint') ]}</em></td></tr>
<tr>
	<td>@{[ T('sqm script') ]}:</td>
	<td>
		<select name='SCRIPT'>
			<option value='piece_of_cake.qos' $selected{'SCRIPT'}{'piece_of_cake.qos'}>@{[ T('sqm piece of cake') ]}</option>
			<option value='layer_cake.qos' $selected{'SCRIPT'}{'layer_cake.qos'}>@{[ T('sqm layer cake') ]}</option>
			<option value='simple.qos' $selected{'SCRIPT'}{'simple.qos'}>@{[ T('sqm simple') ]}</option>
		</select>
	</td>
</tr>
<tr>
	<td>@{[ T('sqm link layer') ]}:</td>
	<td>
		<select name='LINKLAYER'>
			<option value='none' $selected{'LINKLAYER'}{'none'}>@{[ T('sqm none') ]}</option>
			<option value='ethernet' $selected{'LINKLAYER'}{'ethernet'}>@{[ T('sqm ethernet') ]}</option>
			<option value='atm' $selected{'LINKLAYER'}{'atm'}>@{[ T('sqm atm') ]}</option>
			<option value='ptm' $selected{'LINKLAYER'}{'ptm'}>@{[ T('sqm ptm') ]}</option>
		</select>
	</td>
</tr>
<tr>
	<td>@{[ T('sqm overhead') ]}:</td>
	<td><input type='text' name='OVERHEAD' value='@{[ h($settings{'OVERHEAD'}) ]}' size='6' />
	&nbsp; @{[ T('sqm mpu') ]}:
	<input type='text' name='STAB_MPU' value='@{[ h($settings{'STAB_MPU'}) ]}' size='6' /></td>
</tr>
</table>
<h3>@{[ T('sqm advanced') ]}</h3>
<table width='100%'>
<tr>
	<td width='40%'><input type='checkbox' name='NAT' value='on' $checked{'NAT'}{'on'} /> @{[ T('sqm nat') ]}</td>
	<td></td>
</tr>
<tr>
	<td><input type='checkbox' name='DUAL_HOST' value='on' $checked{'DUAL_HOST'}{'on'} /> @{[ T('sqm dual host') ]}</td>
	<td></td>
</tr>
<tr>
	<td><input type='checkbox' name='WASH' value='on' $checked{'WASH'}{'on'} /> @{[ T('sqm wash') ]}</td>
	<td></td>
</tr>
<tr>
	<td><input type='checkbox' name='ACK_FILTER' value='on' $checked{'ACK_FILTER'}{'on'} /> @{[ T('sqm ack filter') ]}</td>
	<td></td>
</tr>
<tr>
	<td>@{[ T('sqm extra ingress') ]}:</td>
	<td><input type='text' name='IQDISC_OPTS' value='@{[ h($settings{'IQDISC_OPTS'}) ]}' size='40' /></td>
</tr>
<tr>
	<td>@{[ T('sqm extra egress') ]}:</td>
	<td><input type='text' name='EQDISC_OPTS' value='@{[ h($settings{'EQDISC_OPTS'}) ]}' size='40' /></td>
</tr>
<tr>
	<td><input type='checkbox' name='SQM_DEBUG' value='1' $checked{'SQM_DEBUG'}{'1'} /> @{[ T('sqm debug') ]}</td>
	<td></td>
</tr>
</table>
<p>
	<input type='submit' name='ACTION' value='@{[ T('sqm save') ]}' />
	<input type='submit' name='ACTION' value='@{[ T('sqm start') ]}' />
	<input type='submit' name='ACTION' value='@{[ T('sqm restart') ]}' />
	<input type='submit' name='ACTION' value='@{[ T('sqm stop') ]}' />
</p>
</form>
END
&Header::closebox();

&Header::openbox('100%', 'left', T('sqm status'));
print "<pre style='white-space:pre-wrap;'>";
if (-x $sqmctrl) {
	my @out = `$sqmctrl status 2>&1`;
	foreach my $line (@out) {
		$line =~ s/&/&amp;/g;
		$line =~ s/</&lt;/g;
		$line =~ s/>/&gt;/g;
		print $line;
	}
} else {
	print "sqmctrl not installed\n";
}
print "</pre>\n";
&Header::closebox();

&Header::closebigbox();
&Header::closepage();
