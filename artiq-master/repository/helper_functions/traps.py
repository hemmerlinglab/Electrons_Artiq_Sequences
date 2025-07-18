traps = {

    "UCB 3 PCB": {
        "amp": False,
        "cfile": "UCB_3PCBTrap.txt",
        "electrodes_order": [
            'tl1', 'tl2', 'tl3', 'tl4', 'tl5',
            'tr1', 'tr2', 'tr3', 'tr4', 'tr5',
            'tg',
            'bl1', 'bl2', 'bl3', 'bl4', 'bl5',
            'br1', 'br2', 'br3', 'br4', 'br5'
        ],
        "multipoles_order": ['Ex', 'Ey', 'Ez', 'U1', 'U2', 'U3', 'U4', 'U5'],
        "elec_zotino_chs": {
                'tg' : 100,
                'tl1' : 0,
                'tl2' : 1,
                'tl3' : 2,
                'tl4' : 3,
                'tl5' : 4,
                'tr1' : 9,
                'tr2' : 8,
                'tr3' : 7,
                'tr4' : 6,
                'tr5' : 5,
                'bl1' : 12,
                'bl2' : 13,
                'bl3' : 14,
                'bl4' : 15,
                'bl5' : 16,
                'br1' : 21,
                'br2' : 20,
                'br3' : 19,
                'br4' : 18,
                'br5' : 17,
            }
            # needle top: channel 10
            # needle bottom: channel 22
            # GND top: channel 11
            # GND bottom: channel 23
            # GND bottom: channel 24
    },

    "UCB 3 PCB Flipped": {
        "amp": False,
        "cfile": "UCB_3PCBTrap.txt",
        "electrodes_order": [
            'tl1', 'tl2', 'tl3', 'tl4', 'tl5',
            'tr1', 'tr2', 'tr3', 'tr4', 'tr5',
            'tg',
            'bl1', 'bl2', 'bl3', 'bl4', 'bl5',
            'br1', 'br2', 'br3', 'br4', 'br5'
        ],
        "multipoles_order": ['Ex', 'Ey', 'Ez', 'U1', 'U2', 'U3', 'U4', 'U5'],
        "elec_zotino_chs": {
                'tg' : 100,
                'tl1' : 12,
                'tl2' : 13,
                'tl3' : 14,
                'tl4' : 15,
                'tl5' : 16,
                'tr1' : 21,
                'tr2' : 20,
                'tr3' : 19,
                'tr4' : 18,
                'tr5' : 17,
                'bl1' : 0,
                'bl2' : 1,
                'bl3' : 2,
                'bl4' : 3,
                'bl5' : 4,
                'br1' : 9,
                'br2' : 8,
                'br3' : 7,
                'br4' : 6,
                'br5' : 5,
            }
            # needle top: channel 22
            # needle bottom: channel 10
            # GND top: channel 23
            # GND top: channel 24
            # GND bottom: channel 11
    },

    "Single PCB": {
        "amp": True,
        "cfile": "SinglePCBTrap.txt",
        "electrodes_order": [
            'tl1', 'tl2', 'tl3', 'tl4', 'tl5',
            'tr1', 'tr2', 'tr3', 'tr4', 'tr5',
            'bl1', 'bl2', 'bl3', 'bl4', 'bl5',
            'br1', 'br2', 'br3', 'br4', 'br5'
        ],
        "multipoles_order": ['Ex', 'Ey', 'Ez', 'U1', 'U2', 'U3', 'U4', 'U5'],
        "elec_zotino_chs": {
            'tl1' : 0,
            'tl2' : 1,
            'tl3' : 2,
            'tl4' : 3,
            'tl5' : 4,
            'tr1' : 9,
            'tr2' : 8,
            'tr3' : 7,
            'tr4' : 6,
            'tr5' : 5,
            'bl1' : 10,
            'bl2' : 11,
            'bl3' : 12,
            'bl4' : 13,
            'bl5' : 14,
            'br1' : 19,
            'br2' : 18,
            'br3' : 17,
            'br4' : 16,
            'br5' : 15,
        }
    },
    
    "Single PCB Flipped": {
        "amp": True,
        "cfile": "SinglePCBTrap.txt",
        "electrodes_order": [
            'tl1', 'tl2', 'tl3', 'tl4', 'tl5',
            'tr1', 'tr2', 'tr3', 'tr4', 'tr5',
            'bl1', 'bl2', 'bl3', 'bl4', 'bl5',
            'br1', 'br2', 'br3', 'br4', 'br5'
        ],
        "multipoles_order": ['Ex', 'Ey', 'Ez', 'U1', 'U2', 'U3', 'U4', 'U5'],
        "elec_zotino_chs": {
            'tl1' : 10,
            'tl2' : 11,
            'tl3' : 12,
            'tl4' : 13,
            'tl5' : 14,
            'tr1' : 19,
            'tr2' : 18,
            'tr3' : 17,
            'tr4' : 16,
            'tr5' : 15,
            'bl1' : 0,
            'bl2' : 1,
            'bl3' : 2,
            'bl4' : 3,
            'bl5' : 4,
            'br1' : 9,
            'br2' : 8,
            'br3' : 7,
            'br4' : 6,
            'br5' : 5,
        }
    }
}
