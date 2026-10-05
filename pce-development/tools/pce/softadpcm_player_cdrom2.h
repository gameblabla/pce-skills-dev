#pragma once

/* Optional CD-ROM² IRQ adapter. The decoder core itself has no CD BIOS calls
 * and can also be used by HuCard software with a native timer vector. */
void pce_softadpcm_install_cdrom2_irq(void);
