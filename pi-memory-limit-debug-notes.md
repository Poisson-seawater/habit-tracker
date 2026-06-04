# Debug Raspberry Pi Docker Memory Limits

Notes prises pendant le diagnostic des limites memoire Docker sur la Raspberry Pi.

## Contexte

Le `docker-compose.yml` du projet definit des limites memoire pour les services:

```yaml
api:
  deploy:
    resources:
      limits:
        memory: 40M

bot:
  deploy:
    resources:
      limits:
        memory: 35M
```

Sur la Pi, les limites inspectees etaient toutes les deux a `0`, ce qui signifie que Docker ne les applique pas.

## Commandes Et Sorties

### 1. Verification des limites Docker appliquees

Commandes demandees:

```bash
docker inspect habit-tracker-api-1 --format '{{.HostConfig.Memory}}'
docker inspect habit-tracker-bot-1 --format '{{.HostConfig.Memory}}'
```

Sortie donnee:

```text
0
0
```

### 2. Verification cgroup Docker

Commande demandee:

```bash
docker info | grep -i cgroup
```

Sortie donnee:

```text
WARNING: No memory limit support
 Cgroup Driver: systemd
WARNING: No swap limit support
 Cgroup Version: 2
  cgroupns
```

### 3. Lecture de la ligne de boot effective

Commande demandee:

```bash
cat /proc/cmdline
```

Sortie donnee:

```text
reboot=w coherent_pool=1M 8250.nr_uarts=1 pci=pcie_bus_safe cgroup_disable=memory numa_policy=interleave nvme.max_host_mem_size_mb=0  numa=fake=8 system_heap.max_order=0 smsc95xx.macaddr=88:A2:9E:A1:3E:B7 vc_mem.mem_base=0x3fc00000 vc_mem.mem_size=0x40000000  console=ttyAMA10,115200 console=tty1 root=PARTUUID=7d23366b-02 rootfstype=ext4 fsck.repair=yes rootwait resize cfg80211.ieee80211_regdom=CA
```

### 4. Recherche de cgroup dans les fichiers cmdline classiques

Commande demandee:

```bash
sudo grep -Hn "cgroup" /boot/firmware/cmdline.txt /boot/cmdline.txt 2>/dev/null
```

Sortie donnee:

```text
rien sort
```

### 5. Inspection des fichiers boot existants

Commande demandee:

```bash
ls -la /boot /boot/firmware /boot/cmdline.txt /boot/firmware/cmdline.txt
```

Sortie donnee:

```text
-rw-r--r-- 1 root root   92 Apr 21 01:06 /boot/cmdline.txt
-rwxr-xr-x 1 root root  131 Jan  1  1980 /boot/firmware/cmdline.txt

/boot:
total 50801
drwxr-xr-x  3 root root     4096 Apr 21 01:12 .
drwxr-xr-x 18 root root     4096 Apr 21 01:06 ..
-rw-r--r--  1 root root       92 Apr 21 01:06 cmdline.txt
-rw-r--r--  1 root root   248974 Mar 11 15:54 config-6.12.75+rpt-rpi-2712
-rw-r--r--  1 root root   248977 Mar 11 15:54 config-6.12.75+rpt-rpi-v8
-rw-r--r--  1 root root       91 Apr 21 01:06 config.txt
drwxr-xr-x  3 root root     4608 Jan  1  1970 firmware
-rw-r--r--  1 root root 16038675 Apr 21 01:12 initrd.img-6.12.75+rpt-rpi-2712
-rw-r--r--  1 root root 16040912 Apr 21 01:12 initrd.img-6.12.75+rpt-rpi-v8
lrwxrwxrwx  1 root root       18 Apr 21 01:12 issue.txt -> firmware/issue.txt
lrwxrwxrwx  1 root root       17 Apr 21 01:06 overlays -> firmware/overlays
-rw-r--r--  1 root root       83 Mar 11 15:54 System.map-6.12.75+rpt-rpi-2712
-rw-r--r--  1 root root       83 Mar 11 15:54 System.map-6.12.75+rpt-rpi-v8
-rw-r--r--  1 root root  9698043 Mar 11 15:54 vmlinuz-6.12.75+rpt-rpi-2712
-rw-r--r--  1 root root  9695883 Mar 11 15:54 vmlinuz-6.12.75+rpt-rpi-v8

/boot/firmware:
total 73544
drwxr-xr-x 3 root root     4608 Jan  1  1970 .
drwxr-xr-x 3 root root     4096 Apr 21 01:12 ..
-rwxr-xr-x 1 root root    32495 Mar 11 15:54 bcm2710-rpi-2-b.dtb
-rwxr-xr-x 1 root root    34687 Mar 11 15:54 bcm2710-rpi-3-b.dtb
-rwxr-xr-x 1 root root    35322 Mar 11 15:54 bcm2710-rpi-3-b-plus.dtb
-rwxr-xr-x 1 root root    33676 Mar 11 15:54 bcm2710-rpi-cm0.dtb
-rwxr-xr-x 1 root root    32258 Mar 11 15:54 bcm2710-rpi-cm3.dtb
-rwxr-xr-x 1 root root    33664 Mar 11 15:54 bcm2710-rpi-zero-2.dtb
-rwxr-xr-x 1 root root    33664 Mar 11 15:54 bcm2710-rpi-zero-2-w.dtb
-rwxr-xr-x 1 root root    56253 Mar 11 15:54 bcm2711-rpi-400.dtb
-rwxr-xr-x 1 root root    56249 Mar 11 15:54 bcm2711-rpi-4-b.dtb
-rwxr-xr-x 1 root root    56770 Mar 11 15:54 bcm2711-rpi-cm4.dtb
-rwxr-xr-x 1 root root    39913 Mar 11 15:54 bcm2711-rpi-cm4-io.dtb
-rwxr-xr-x 1 root root    53760 Mar 11 15:54 bcm2711-rpi-cm4s.dtb
-rwxr-xr-x 1 root root    78748 Mar 11 15:54 bcm2712d0-rpi-5-b.dtb
-rwxr-xr-x 1 root root    78740 Mar 11 15:54 bcm2712-d-rpi-5-b.dtb
-rwxr-xr-x 1 root root    78700 Mar 11 15:54 bcm2712-rpi-500.dtb
-rwxr-xr-x 1 root root    78744 Mar 11 15:54 bcm2712-rpi-5-b.dtb
-rwxr-xr-x 1 root root    79689 Mar 11 15:54 bcm2712-rpi-cm5-cm4io.dtb
-rwxr-xr-x 1 root root    79755 Mar 11 15:54 bcm2712-rpi-cm5-cm5io.dtb
-rwxr-xr-x 1 root root    79730 Mar 11 15:54 bcm2712-rpi-cm5l-cm4io.dtb
-rwxr-xr-x 1 root root    79796 Mar 11 15:54 bcm2712-rpi-cm5l-cm5io.dtb
-rwxr-xr-x 1 root root    52624 Apr 21 01:05 bootcode.bin
-rwxr-xr-x 1 root root      131 Jan  1  1980 cmdline.txt
-rwxr-xr-x 1 root root     1247 Apr 21 01:06 config.txt
-rwxr-xr-x 1 root root     3272 Apr 21 01:05 fixup4cd.dat
-rwxr-xr-x 1 root root     5498 Apr 21 01:05 fixup4.dat
-rwxr-xr-x 1 root root     8491 Apr 21 01:05 fixup4db.dat
-rwxr-xr-x 1 root root     8493 Apr 21 01:05 fixup4x.dat
-rwxr-xr-x 1 root root     3272 Apr 21 01:05 fixup_cd.dat
-rwxr-xr-x 1 root root     7367 Apr 21 01:05 fixup.dat
-rwxr-xr-x 1 root root    10334 Apr 21 01:05 fixup_db.dat
-rwxr-xr-x 1 root root    10336 Apr 21 01:05 fixup_x.dat
-rwxr-xr-x 1 root root 16038675 Apr 21 01:12 initramfs_2712
-rwxr-xr-x 1 root root 16040912 Apr 21 01:12 initramfs8
-rwxr-xr-x 1 root root      145 Apr 21 01:12 issue.txt
-rwxr-xr-x 1 root root  9698043 Apr 21 01:05 kernel_2712.img
-rwxr-xr-x 1 root root  9695883 Apr 21 01:05 kernel8.img
-rwxr-xr-x 1 root root     1594 Apr 21 01:05 LICENCE.broadcom
-rwxr-xr-x 1 root root      921 Apr 21 01:07 meta-data
-rwxr-xr-x 1 root root     1730 Apr 21 01:07 network-config
drwxr-xr-x 2 root root    31744 Apr 21 01:05 overlays
-rwxr-xr-x 1 root root   850300 Apr 21 01:05 start4cd.elf
-rwxr-xr-x 1 root root  3802024 Apr 21 01:05 start4db.elf
-rwxr-xr-x 1 root root  2303680 Apr 21 01:05 start4.elf
-rwxr-xr-x 1 root root  3051304 Apr 21 01:05 start4x.elf
-rwxr-xr-x 1 root root   850300 Apr 21 01:05 start_cd.elf
-rwxr-xr-x 1 root root  4873960 Apr 21 01:05 start_db.elf
-rwxr-xr-x 1 root root  3027872 Apr 21 01:05 start.elf
-rwxr-xr-x 1 root root  3774952 Apr 21 01:05 start_x.elf
-rwxr-xr-x 1 root root     3277 Apr 21 01:07 user-data
```

### 6. Lecture de `/boot/cmdline.txt`

Commande demandee:

```bash
cat /boot/cmdline.txt
```

Sortie donnee:

```text
DO NOT EDIT THIS FILE

The file you are looking for has moved to /boot/firmware/cmdline.txt
```

### 7. Lecture de `/boot/firmware/cmdline.txt`

Commande demandee:

```bash
cat /boot/firmware/cmdline.txt
```

Sortie donnee:

```text
console=serial0,115200 console=tty1 root=PARTUUID=a3f07636-02 rootfstype=ext4 fsck.repair=yes rootwait cfg80211.ieee80211_regdom=CA
```

### 8. Verification des montages avec `findmnt`

Commande demandee:

```bash
findmnt -no SOURCE,TARGET,FSTYPE / /boot /boot/firmware
```

Sortie donnee:

```text
rien
```

### 9. Verification des montages avec `df`

Commande demandee:

```bash
df -hT / /boot /boot/firmware
```

Sortie donnee:

```text
Filesystem     Type  Size  Used Avail Use% Mounted on
/dev/mmcblk0p2 ext4  117G  5.5G  107G   5% /
/dev/mmcblk0p2 ext4  117G  5.5G  107G   5% /
/dev/mmcblk0p1 vfat  505M   74M  432M  15% /boot/firmware
```

### 10. Verification des PARTUUID

Commande demandee:

```bash
lsblk -o NAME,FSTYPE,SIZE,MOUNTPOINTS,PARTUUID
```

Sortie donnee:

```text
NAME        FSTYPE   SIZE MOUNTPOINTS   PARTUUID
loop0       swap     106M
mmcblk0            119.2G
├─mmcblk0p1 vfat     512M /boot/firmware
│                                       a3f07636-01
└─mmcblk0p2 ext4   118.7G /             a3f07636-02
zram0       swap       2G [SWAP]
```

### 11. Reverification de la ligne de boot effective

Commande demandee:

```bash
cat /proc/cmdline
```

Sortie donnee:

```text
reboot=w coherent_pool=1M 8250.nr_uarts=1 pci=pcie_bus_safe cgroup_disable=memory numa_policy=interleave nvme.max_host_mem_size_mb=0  numa=fake=8 system_heap.max_order=0 smsc95xx.macaddr=88:A2:9E:A1:3E:B7 vc_mem.mem_base=0x3fc00000 vc_mem.mem_size=0x40000000  console=ttyAMA10,115200 console=tty1 root=PARTUUID=7d23366b-02 rootfstype=ext4 fsck.repair=yes rootwait resize cfg80211.ieee80211_regdom=CA
```

### 12. Recherche large dans `/boot/firmware`

Commande demandee:

```bash
sudo grep -RIn "cgroup_disable\|cgroup_enable\|7d23366b\|a3f07636\|cmdline\|kernel\|os_prefix" /boot/firmware
```

Sortie donnee:

```text
Sortie trop volumineuse. Diagnostic mis en pause avant analyse de cette sortie.
```

## Ce Qu'on A Appris

1. Docker ne respecte pas actuellement les limites memoire sur la Pi: `HostConfig.Memory` retourne `0` pour `api` et `bot`.

2. Docker confirme le probleme cote hote avec:

```text
WARNING: No memory limit support
WARNING: No swap limit support
```

3. La cause directe visible est dans `/proc/cmdline`:

```text
cgroup_disable=memory
```

Ce parametre desactive explicitement le controleur memoire cgroup au boot. Tant qu'il est present dans la ligne de commande effective du kernel, Docker ne peut pas appliquer les limites RAM.

4. Le fichier `/boot/cmdline.txt` ne doit pas etre modifie: il indique lui-meme que le fichier reel a bouge vers `/boot/firmware/cmdline.txt`.

5. `/boot/firmware/cmdline.txt` ne contient pas `cgroup_disable=memory`; il contient seulement une ligne simple avec `root=PARTUUID=a3f07636-02`.

6. Il y a une incoherence importante entre:

```text
/boot/firmware/cmdline.txt -> root=PARTUUID=a3f07636-02
/proc/cmdline              -> root=PARTUUID=7d23366b-02
```

Selon `lsblk`, le systeme monte actuellement `/` depuis `a3f07636-02`. Pourtant `/proc/cmdline` annonce `7d23366b-02`. Cette incoherence doit etre comprise avant de modifier les fichiers boot.

7. La prochaine investigation devrait chercher qui ajoute ou remplace la ligne de commande kernel effective. Les pistes probables sont:

- le firmware Raspberry Pi qui complete ou remplace des arguments boot;
- un fichier de configuration dans `/boot/firmware/config.txt`;
- un `bootargs` integre dans un fichier device tree `.dtb`;
- un mecanisme de boot cloud-init / image preconfiguree, vu la presence de `user-data`, `meta-data` et `network-config`.

## Prochaine Etape Proposee

Reprendre avec une recherche plus ciblee, pour eviter une sortie trop massive:

```bash
sudo grep -In "cmdline\|kernel\|os_prefix\|auto_initramfs" /boot/firmware/config.txt
```

Puis, si besoin:

```bash
sudo strings /boot/firmware/bcm2712-rpi-5-b.dtb | grep -i "cgroup\|7d23366b\|bootargs"
```
