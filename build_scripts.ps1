# $CommonArguments = @{
#   noconfirm = $true;
#   "log-level" = "WARN";
#   onefile = $true;
# }

# pyinstaller.exe `
# 	@CommonArguments `
# 	'.\tests\Change - Close all REVIEW.py';
	
# pyinstaller.exe `
# 	@CommonArguments `
# 	'.\tests\Change - IMPL to REVIEW.py';
	




pyinstaller.exe --noconfirm --log-level=WARN --onefile --specpath='.\build_spec' '.\src\Change - Close all REVIEW.py'
pyinstaller.exe --noconfirm --log-level=WARN --onefile --specpath='.\build_spec' '.\src\Change - IMPL to REVIEW.py'