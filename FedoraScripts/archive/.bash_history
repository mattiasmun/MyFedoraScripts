auto_clicker_gui
bc -lq
bg
btop
c
cat "$HOME/.git-credentials"
cat "$HOME/.gitconfig"
cat "$HOME/.gitignore_global"
cat "$HOME/.local/share/Steam/steamapps/workshop/content/1128860/3271667155/scene/set/stuff/rifle"
cat "$HOME/.local/share/Steam/steamapps/workshop/content/1128860/3360488425/scene/set/difficulty/easy.inc"
cat "$HOME/.local/share/Steam/steamapps/workshop/content/1128860/3360488425/scene/set/difficulty/novice.inc"
cd
cd "$HOME/.local/share/Steam/steamapps/common/Men of War II"
cd "$HOME/.local/share/Steam/steamapps/common/Men of War II/packages/main/scene/entity"
cd "$HOME/.local/share/Steam/steamapps/workshop/content/1128860"
cd "$HOME/Men of War II/packages/Unit_booster"
cd "$HOME/Men of War II/packages/Unit_booster/scene/entity"
cd "$HOME/Men of War II/packages/Unit_booster/scene/set/breed/arena_mp/usa"
cd "$HOME/Men of War II/packages/editor-local-changes/global"
cd -- -vehicle
cd ..
clamdscan --stream "$HOME/.clamtk/attachment"
clamscan_filter.sh
closeall
conditional_7z_backup.sh
conditional_7z_backup.sh "$HOME/Men of War II/packages/Unit_booster"
cp requirements.txt $HOME/Bash/MyFedoraScripts/FedoraScripts/archive/requirements.txt
d
d $(tu 21:00:00)
df
df -h
dnf --help
dnf --version
dnf -v
dnf check
dnf check-upgrade
dnf group list
dnf history info last
dnf history list
dnf history list | more
dnf list installed | grep @
dnf repoquery --duplicates
dnf repoquery --extras
dnf repoquery --help
dnf repoquery --installonly
dnf repoquery --leaves
dnf repoquery --unneeded
dnf repoquery --userinstalled --queryformat '%{name}.%{arch} \\n'
dnf search pikepdf
dnfsysupgr
dnfusrins
doc_converter.py --help
doc_converter.py -s -i Dokument/Input -o Dokument/Output
dotool --help
dotool --list-keys
dotoold &
du
du $temp_file
du --help
du -c
du -h
du car
echo $((1+2))
echo $PATH
echo $SHELL
echo $XDG_SESSION_TYPE
echo $temp_file
echo key k:26 k:39 k:40 | dotoolc
echo key leftmeta | dotoolc
echo key shift+1 x:exclam shift+k:2 | dotoolc
env
ex --help
exit
ffprobe --help
ffprobe output.mp3
fg
find . -name "*~"
find . -name "*~" -delete
find . -type f -name '*++*'
find . -type f -name '*++*' -print0 | while IFS= read -r -d $'\0' old_path; do     new_path="${old_path//++/+}";          if [ "$old_path" != "$new_path" ]; then         echo "PREVIEW: '$old_path' -> '$new_path'";     fi; done
find . -type f -name '*++*' -print0 | while IFS= read -r -d $'\0' old_path; do     new_path="${old_path//++/+}";          if [ "$old_path" != "$new_path" ]; then         mv -v -- "$old_path" "$new_path";     fi; done
find_and_sort_files .
find_and_sort_files female
flatpak list
flatpak run com.valvesoftware.Steam steam://rungameid/1066780
flatpak update -y
for file in "$HOME/.bash_history" "$HOME/Bash/MyFedoraScripts/FedoraScripts/archive/.bash_history"; do cp "$HOME/.bash_history2" "$file"; done
for file in "$HOME/Men of War II/packages/Unit_booster/scene/entity/-vehicle/car/opel_blitz/opel_blitz_supp+.def" "$HOME/Men of War II/packages/Unit_booster/scene/entity/-vehicle/car/opel_blitz_highback/opel_blitz_highback+.def" "$HOME/Men of War II/packages/Unit_booster/scene/entity/-vehicle/car/gmc/gmc_supp+.def" "$HOME/Men of War II/packages/Unit_booster/scene/entity/-vehicle/car/gmc_inf/gmc_inf+.def" "$HOME/Men of War II/packages/Unit_booster/scene/entity/-vehicle/car/gaz_aa_untented/gaz_aa_untented+.def"; do cp "$HOME/Men of War II/packages/Unit_booster/scene/entity/-vehicle/car/gaz_aa/gaz_aa_supp+.def" "$file"; done
fuck
fuck --help
fzf --multi --cycle
fzf-select-open.sh
gedit "$HOME/Men of War II/log/game.log"
git --help
git add *
git clone https://git.sr.ht/~geb/dotool
git gc
git gc --prune=now
git lfs install
git lfs track "FedoraScripts/dist/*"
git lfs track "dist/doc_converter_cli"
git pull
git push
git push origin --force --all
git reflog expire --expire=now --all
git rev-list --objects --all | grep "$(git for-each-ref --format='%(objectname) %(refname)' refs/heads | cut -d' ' -f1)" | git cat-file --batch-check='%(objecttype) %(objectsize) %(rest)' | sort -n -k2 | tail -10
git status
gitcfg
gitty ~/529340
gitty ~/Bash/MyFedoraScripts
gnome-shell --version
grep -Ii -d skip dead_greek /usr/share/X11/locale/en_US.UTF-8/Compose
grep -nirI "supp+"
groupadd -f input
groups
gs
gs --help
htop
id -nG
javacfg
jedit
l
lame --help
lame --longhelp
ll
ln --help
locate "*.py" | while IFS= read -r file; do ls -ld "$file"; done
locate "+.def" | while IFS= read -r file; do ls -ld "$file"; done
locate "1927_cannon" | while IFS= read -r file; do ls -ld "$file"; done
locate "Men of War II" | while IFS= read -r file; do ls -ld "$file"; done
locate "bm31+" | while IFS= read -r file; do ls -ld "$file"; done
locate "m30+" | while IFS= read -r file; do ls -ld "$file"; done
locate "rocketpdf" | while IFS= read -r file; do ls -ld "$file"; done
locate "su122+" | while IFS= read -r file; do ls -ld "$file"; done
locate "supp+" | while IFS= read -r file; do ls -ld "$file"; done
ls
ls -Al
lsattr Dokument/IDLE_py.py
lsblk
lspci
make
man dotool
man fzf
man ocrmypdf
man wlrctl
mediainfo
meld "$HOME/.bash_history" "$HOME/.bash_history2" "$HOME/Bash/MyFedoraScripts/FedoraScripts/archive/.bash_history" &
meld "$HOME/.local/share/Steam/steamapps/workshop/content/1128860/3360488425/scene/set/difficulty/easy.inc" "$HOME/.local/share/Steam/steamapps/workshop/content/1128860/3360488425/scene/set/difficulty/novice.inc" &
meld "$HOME/Dokument/IDLE_py.py" "$HOME/Bash/MyFedoraScripts/FedoraScripts/archive/IDLE_py.py" &
meld "$temp_file" "$HOME/Bash/MyFedoraScripts/FedoraScripts/doc_converter.py" &
meld &
meld * &
mkdir --help
more --help
mpg123
mplayer
nautilus .
newton_raphson
nslookup duckduckgo.com
nslookup google.com
nslookup google.com 8.26.56.26
numeric_derivative
nvidia-smi
nvtop
ocr_optimize_cli.py --help
ocr_optimize_cli.py $HOME/Dokument/Input --output_dir $HOME/Dokument/Output
ocr_optimize_cli.py $HOME/Dokument/Input -o $HOME/Dokument/Output
pdf_optimizer.py --help
pdf_optimizer.py -i Dokument/Input
pdf_optimizer.py -i Input
pgrep firefox
pgrep flatpak
pgrep thunderbird
pip list
pip list --user
pip list --user | tail -n +3 | awk '{print $1}' > $HOME/Bash/MyFedoraScripts/FedoraScripts/archive/requirements.txt
pip3 install pip-date pyautogui pynput rocketpdf tsp-solver2
pip3 list --user
pip3 list --user --outdated
pip3update
pkill -sigkill Civ6
pkill -sigkill TransportFever2
pkill -sigkill mow2
pkill firefox
pngquant --version
py
pyenv
pyinstaller --onefile --name doc_converter_cli doc_converter.py
pyinstaller --onefile --name pdf_optimizer_cli pdf_optimizer.py
qpdf
qpdf --help
qpdf --help=exit-status
r
remove-retired-packages
rm $temp_file
rm -r 3553934930/global/sound/human/talk/rus_medic_female 3553934930/global/sound/human/talk/rus_sniper_female
rm 3553934930/scene/entity_soviet_female.pak 3553934930/global/interface/scene/portrait/rus_sniper_female.png 3553934930/global/interface/scene/portrait/rus_medic_female.png
rm ~/.bash_history-*.tmp
rocketpdf --help
rsync -avz --update "$HOME/Men of War II/packages/Unit_booster.7z" "$HOME/Bash/MyFedoraScripts/FedoraScripts/archive/mow2/"
setup-my-env.sh
sha256sum Hämtningar/Fedora-Workstation-Live-42-1.1.x86_64.iso
snap --help
snap list
snap refresh --list
snap refresh --time
source ~/.bashrc
stat /
steam steam://rungameid/1128860
strcmp asdfsdf gertergdfg
sudo -A ./build.sh install
sudo -A dnf -y system-upgrade download --refresh --allowerasing --releasever=43 &
sudo -A dnf autoremove
sudo -A dnf check
sudo -A dnf check-update --refresh
sudo -A dnf clean all
sudo -A dnf system-upgrade reboot
sudo -A dnf upgrade
sudo -A dnf upgrade --best --allowerasing
sudo -A dnf-automatic
sudo -A gedit /etc/clamd.d/scan.conf &
sudo -A gedit /etc/dnf/automatic.conf &
sudo -A gedit /etc/freshclam.conf &
sudo -A make install
sudo -A meld /etc/dnf/automatic.conf /usr/share/dnf5/dnf5-plugins/automatic.conf
sudo -A snap install hello-world
sudo -A snap install powershell
sudo -A systemctl reset-failed
sudo -A systemctl restart gdm
sudo -A systemctl status clamav-freshclam
sudo -A systemctl status clamd@scan.service
sudo -A updatedb
systemctl --user status dotool.service
systemctl enable --now dnf5-automatic.timer
systemctl status
systemctl status bluetooth
systemctl status clamav-freshclam
systemctl status clamav-freshclam.service
systemctl status clamd@scan
systemctl status clamd@scan.service
systemctl status dnf5-automatic.service
systemctl status dnf5-automatic.timer
temp_file=$(mktemp)
time find_and_sort_files .
uname -a
uname -r
unique_lines
update-alternatives
update-alternatives --list
users
wc -l "$HOME/Bash/MyFedoraScripts/FedoraScripts/progs"
wc -lL .bash_history
wc -lL .bash_history2
wc -lL < .bash_history
wc -lL < .bash_history2
wev
who
who -a
who -r
who -u
whoami
wlrctl --help
wlrctl keyboard type "Hello, world!"
wlrctl pointer move 50 -70
wlrctl window focus firefox
wmctrl -xl
xdg-open "$HOME/.local/share/Steam/steamapps/common/Men of War II/packages/main/scene/entity/-vehicle/tank_medium/su122.pak"
xev
yev
yt-dlp -F https://www.youtube.com/watch?v=E9lVXoezkFM
yt-dlp -f 140 https://www.youtube.com/watch?v=E9lVXoezkFM
z --help
z Fe
zoxide --help
zoxide add "$HOME/Bash/MyFedoraScripts/FedoraScripts"
zoxide add --help
zoxide edit
