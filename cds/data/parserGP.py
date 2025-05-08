import weakref
import xml.etree.ElementTree as ET

from music21 import *
from music21.base import ElementWrapper

from hammeron_pulloff import Hammer_on, Pull_off

# TODO Ecrire des commentaire python typique


class ParserGP(converter.subConverters.SubConverter):

    registerFormats = ("gpif",)
    registerInputExtensions = ("gpif",)

    @staticmethod
    def _make_metronomeMark(tempo_value: str) -> tempo.MetronomeMark:
        bpm, ref = tempo_value.split(" ")
        bpm = int(bpm)
        ref = int(ref)
        mark = tempo.MetronomeMark(number=bpm, referent=ref / 2)
        return mark

    def parseFile(self, XMLFileName, number=None):
        # root is the GPIF node at the top of the gpif file
        # with open(XMLFileName,'r',encoding="utf-8-sig") as xml_file:
        #     xml_tree = ET.parse(xml_file)
        #     self.root = xml_tree.getroot()
        #     self.__initScore())
        # Reset self.stream for each file
        self.stream = stream.Score()
        # List to store all Hammer-Ons and Pull-Offs (hopos)
        self.hopos = []
        self.notes_with_slide_to_next = []
        self.root = ET.parse(XMLFileName).getroot()
        self.__initScore()
        return self.stream

    # Create a Stream structure (Score > Part > Measure > Voice > Notes) according to xml
    def __initScore(self):
        # Set Score metadatas
        # self.stream.metadata = metadata.Metadata(title=self.tree.xpath("/GPIF/Score/Title")[0].text)
        # """La valeur 'stream'.metadata.title prend en compte le titre de la musique et l'artiste, séparés par un \n"""

        titre = "No title"
        sous_titre = ""
        artiste = "No artist"
        tag_titre = self.root.find("./Score/Title")
        tag_sous_titre = self.root.find("./Score/SubTitle")
        tag_artiste = self.root.find("./Score/Artist")
        if tag_titre is not None:
            titre = tag_titre.text
        if tag_sous_titre is not None:
            sous_titre = tag_sous_titre.text
        if tag_artiste is not None:
            artiste = str(tag_artiste.text)

        # nom_complet = titre+'\n'+artiste+'\n'+sous_titre
        # meta = metadata.Metadata(title=nom_complet)

        meta = metadata.Metadata()
        meta.title = titre
        meta.alternativeTitle = sous_titre

        artist_contributor = metadata.Contributor()
        artist_contributor.name = artiste
        artist_contributor.role = "artist"
        meta.addContributor(artist_contributor)

        self.stream.metadata = meta

        # Detect anacrusis
        anacrusis = self.root.find("./MasterTrack/Anacrusis") is not None

        # Extract tempo information
        for automation in self.root.findall(
            "./MasterTrack/Automations/Automation"
        ):
            if automation.find("./Type").text == "Tempo":
                metronome_mark = self._make_metronomeMark(
                    automation.find("./Value").text
                )
        self.stream.append(metronome_mark)
        # Create Part according to normally tuned guitar tracks
        for track in self.root.findall("./Tracks/Track"):
            # Select track according to icon (guitar icons) and tunning (standard tuning) and track.find(".//*[@name='Tuning']/Pitches").text == "40 45 50 55 59 64"
            if track.find("./IconId").text in [
                "1",
                "2",
                "4",
                "5",
                "23",
                "24",
                "25",
                "26",
                "22",
            ]:
                p = stream.Part()
                part_name = track.find("./Name").text
                # part_name = part_name.replace(' ','').replace('\n','')
                p.partName = part_name
                part_short_name = track.find("./ShortName").text
                if part_short_name is not None:
                    part_short_name = part_short_name.replace(" ", "").replace(
                        "\n", ""
                    )
                    p.partAbbreviation = part_short_name

                instrument_set_node = track.find("./InstrumentSet")
                instrument_name = instrument_set_node.find("./Name").text
                instrument_type = instrument_set_node.find("./Type").text
                # p.insert(0,clef.TabClef())
                p.id = track.get("id")
                tuning = track.find(".//*[@name='Tuning']/Pitches").text
                tuning = tuning.split(" ")
                tuning = [pitch.Pitch(int(p)) for p in tuning]
                fretboard = tablature.GuitarFretBoard()
                fretboard.tuning = tuning
                self.stream.insert(0, ElementWrapper(fretboard))
                self.stream.append(p)
            else:
                print(
                    "Unfitted track (tuned differently or non guitar icon) : "
                    + track.find("Name").text
                )
                raise TypeError()
        partTab = []
        # Append Measures into a temp tab whitch will be append later in parts
        for part in self.stream.parts:
            mtab = []
            tmpTime = ""

            """"""
            #
            prev_key_sig = (
                0  # Ancienne tonalité initialisée à 0 # et 0 b au début
            )
            prev_scale = None
            #
            """"""
            tabclef_added = False
            for masterBar in self.root.findall("./MasterBars/MasterBar"):
                time = masterBar.find("./Time").text
                bar = masterBar.find("./Bars")

                """AJOUT DES DIESES ET BEMOLS"""
                """"""
                #
                armure = masterBar.find(
                    "./Key/AccidentalCount"
                ).text  # --> armure est un str : '0' , '-1' , '2'
                mode = masterBar.find("./Key/Mode").text.lower()
                key_sig = key.KeySignature(int(armure))
                scale = key_sig.asKey(mode)
                #
                """"""
                # Fetch actual bar number to create stream.Measure object
                m = stream.Measure(
                    number=int(bar.text) if anacrusis else int(bar.text) + 1
                )
                # m = stream.Measure()
                # if time != tmpTime:
                #    m.timeSignature = meter.TimeSignature(time)
                m.timeSignature = meter.TimeSignature(time)

                """"""
                #
                if key_sig != prev_key_sig:
                    m.keySignature = key_sig

                key_sig = prev_key_sig
                #

                if scale != prev_scale:
                    m.insert(0, scale)

                prev_scale = scale

                """"""
                if not tabclef_added:
                    m.insert(0, clef.TabClef())
                    tabclef_added = True
                """"""

                tmpTime = time
                m.id = bar.text.split()[int(part.id)]
                # m.number = bar.text
                mtab.append(m)
            partTab.append(mtab)

        # Append Voices into previously created measure
        for i in range(len(partTab)):
            for j in range(len(partTab[i])):
                simileMark = self.root.find(
                    "./Bars/Bar[@id='" + partTab[i][j].id + "']/SimileMark"
                )
                if simileMark is not None:
                    # if there is a simile mark we go back to the previous measure element
                    if simileMark.text == "Simple":
                        for index, voice in enumerate(partTab[i][j - 1].voices):
                            v = stream.Voice()
                            v.id = index + 1
                            v.idGpif = voice.idGpif
                            partTab[i][j].append(v)
                    else:
                        # for double simile mark we go back 2 measure before
                        for index, voice in enumerate(partTab[i][j - 2].voices):
                            v = stream.Voice()
                            v.id = index + 1
                            v.idGpif = voice.idGpif
                            partTab[i][j].append(v)
                else:
                    # When there is no simile mark we fetch voices in XML file
                    for voices in self.root.findall(
                        "./Bars/Bar[@id='" + partTab[i][j].id + "']/Voices"
                    ):
                        for index, idVoice in enumerate(voices.text.split()):
                            # Voice is a list of 4 ids where -1 means there is no voice
                            if idVoice != "-1":
                                v = stream.Voice()
                                v.id = index + 1
                                v.idGpif = idVoice
                                partTab[i][j].append(v)
        self.__addNotestoScore(partTab)
        for i, p in enumerate(partTab):
            for m in p:
                self.stream.parts[i].append(m)
        # create missing slides
        for n_stream in self.stream.flatten().notes:
            n = None
            if isinstance(n_stream, chord.Chord):
                for n_chord in n_stream.notes:
                    if n_chord.slideToNext:
                        n = n_stream
                        for art in n_chord.articulations:
                            if art.name == "string indication":
                                n_string = art.number
                                break
                        break
            else:
                if n_stream.slideToNext:
                    n = n_stream
                    for art in n_stream.articulations:
                        if art.name == "string indication":
                            n_string = art.number
                            break
            if n is not None:
                break  # TODO clean and fix here. It breaks with key/keySignatures
                next_note = n.next()
                while not isinstance(next_note, (note.Note, chord.Chord)):
                    # Iterate over next item until the next note in the stream is found
                    # necessary when a slide is between two measures
                    # CAN DO WEIRD THINGS IF LAST NOTE OF A PART HAS slideToNext
                    # This should not happen in a correct tab so it is not caught
                    print(next_note)
                    next_note = next_note.next()
                if isinstance(next_note, chord.Chord):
                    # add slide on the note that is on the same string
                    done = False
                    for chord_note in next_note.notes:
                        for art in chord_note.articulations:
                            if art.name == "string indication":
                                if art.number == n_string:
                                    chord_note.articulations.append(
                                        articulations.IndeterminateSlide()
                                    )
                                    done = True
                                    break
                        if done:
                            break
                else:
                    next_note.articulations.append(
                        articulations.IndeterminateSlide()
                    )
        # Create all hopos
        for hopo in self.hopos:
            if len(hopo) != 2:
                continue
            start = [
                a.number
                for a in hopo[0].articulations
                if a.name == "fret indication"
            ][0]
            end = [
                a.number
                for a in hopo[1].articulations
                if a.name == "fret indication"
            ][0]
            if start > end:
                spanner = Pull_off(hopo)
            elif start < end:
                spanner = Hammer_on(hopo)
            else:
                skip = False
                for art in hopo[0].articulations:
                    if isinstance(art, articulations.Mute):
                        skip = True
                if skip:
                    continue
                raise ValueError(
                    "There can't be a hopo between two identical notes"
                )
            self.stream.insert(0, spanner)

    # Add all notes from xml in the structure previously created
    def __addNotestoScore(self, partTab):

        # new_fun = '' #Variable qui prendra les valeurs fun:solo ou fun:acc selon la nature de la mesure

        """Indique si le bouton LetRing sur tout le morceau a été activé dans GuitarPro"""
        letring_throughout = self.root.find(
            "./Tracks/Track[@id='0']/LetRingThroughout"
        )
        self.stream.letRingThroughout = letring_throughout is not None
        for i in range(len(partTab)):
            for j in range(len(partTab[i])):
                for v, voice in enumerate(partTab[i][j].voices):
                    offset = 0.0
                    beats = self.root.findall(
                        "./Voices/Voice[@id='" + str(voice.idGpif) + "']/Beats"
                    )
                    if len(beats):
                        # Browse all beats in the voice
                        for idBeat in beats[0].text.split():
                            notesEl = self.root.findall(
                                "./Beats/Beat[@id='" + idBeat + "']/Notes"
                            )
                            cXML = self.root.findall(
                                "./Beats/Beat[@id='" + idBeat + "']/Chord"
                            )

                            """"""
                            #
                            legato = self.root.find(
                                "./Beats/Beat[@id='" + idBeat + "']/Legato"
                            )
                            if legato != None:
                                val_origin = legato.get(
                                    "origin"
                                )  # val_origin/desination : str -> 'true' ou 'false'
                                val_destination = legato.get("destination")

                            fun = self.root.find(
                                "./Beats/Beat[@id='" + idBeat + "']/FreeText"
                            )

                            VibratoWTremBar = self.root.find(
                                "./Beats/Beat[@id='"
                                + idBeat
                                + "']/Properties/Property[@name='VibratoWTremBar']"
                            )
                            Whammy = self.root.find(
                                "./Beats/Beat[@id='" + idBeat + "']/Whammy"
                            )

                            chordName = None
                            graceXML = self.root.findall(
                                "./Beats/Beat[@id='" + idBeat + "']/GraceNotes"
                            )
                            c = None
                            if len(cXML):  # GESTION DES LYRICS POUR LES CHORDS
                                idChord = cXML[0].text
                                chordName = self.root.find(
                                    "./Tracks/Track/Staves/Staff/Properties/Property[@name='DiagramCollection']/Items/Item[@id='"
                                    + idChord
                                    + "']"
                                ).get("name")

                            if len(notesEl):
                                idNotes = notesEl[0].text.split()
                                notes = []
                                bend = None
                                lr = None
                                vibwide = None
                                slide = None
                                mute = None
                                for idNote in idNotes:

                                    """"""
                                    """BOUT DE CODE RECUPERATION DE LET-RING, LIAISONS (legato gp)
                                    ,INDICATEURS DE MESURES SOLO ou ACCOMPAGNEMENT(RYTHMIQUE), BEND ..."""
                                    #
                                    if lr == None:
                                        lr = self.root.find(
                                            "./Notes/Note[@id='"
                                            + idNote
                                            + "']/LetRing"
                                        )
                                    if vibwide == None:
                                        vibwide = self.root.find(
                                            "./Notes/Note[@id='"
                                            + idNote
                                            + "']/Vibrato"
                                        )

                                    if bend == None:
                                        bend = self.root.find(
                                            "./Notes/Note[@id='"
                                            + idNote
                                            + "']/Properties/Property[@name='Bended']/Enable"
                                        )

                                    ####################################
                                    ####################################

                                    if slide == None:
                                        slide = self.root.find(
                                            "./Notes/Note[@id='"
                                            + idNote
                                            + "']/Slide"
                                        )

                                    ####################################
                                    ####################################

                                    Notelr = self.__getNoteFromId(
                                        idBeat, idNote
                                    )
                                    if lr is not None:
                                        Notelr.tie = tie.Tie("let-ring")
                                    """NUMERO DE LA CORDE ET DE LA FRETTE AJOUTES EN PAROLE"""
                                    Notelr.addLyric(
                                        "ST"
                                        + str(
                                            self.root.find(
                                                "./Notes/Note[@id='"
                                                + idNote
                                                + "']/Properties/Property[@name='String']/String"
                                            ).text
                                        )
                                    )
                                    Notelr.addLyric(
                                        "FR"
                                        + str(
                                            self.root.find(
                                                "./Notes/Note[@id='"
                                                + idNote
                                                + "']/Properties/Property[@name='Fret']/Fret"
                                            ).text
                                        )
                                    )

                                    if legato != None:
                                        if val_origin == "true":
                                            if val_destination == "false":
                                                Notelr.addLyric("\___")
                                            else:
                                                Notelr.addLyric("____")
                                        else:
                                            Notelr.addLyric("___/")

                                    if lr != None:
                                        Notelr.addLyric("LetRing")

                                    if letring_throughout != None:
                                        Notelr.addLyric("LetRing")

                                    if fun != None:
                                        Notelr.addLyric(fun.text)

                                    if VibratoWTremBar != None:
                                        Notelr.addLyric("\\/\\/\\/")

                                    if Whammy != None:
                                        Notelr.addLyric("w/bar")

                                    if bend != None:
                                        Notelr.addLyric("<bend>")

                                    if vibwide != None:
                                        Notelr.addLyric("~~~")

                                    #
                                    """"""

                                    notes.append(Notelr)

                                if len(notes) > 1:

                                    notes = chord.Chord(notes)

                                    """AJOUT DES LETRING ET FUN:ACC / FUN:SOLO POUR DES CHORDS"""
                                    #
                                    if lr != None:
                                        notes.addLyric("LetRing")

                                    if letring_throughout != None:
                                        notes.addLyric("LetRing")

                                    if fun != None:
                                        notes.addLyric(fun.text)

                                    if VibratoWTremBar != None:
                                        notes.addLyric("\\/\\/\\/")

                                    if bend != None:
                                        notes.addLyric("<bend>")

                                    if vibwide != None:
                                        notes.addLyric("~~~")

                                    if Whammy != None:
                                        notes.addLyric("w/bar")

                                    #
                                    """"""

                                # TODO : ajouter les labels d'accords dans un champs dédié dans music21 ? (plutôt que dans lyrics)
                                if chordName:
                                    if isinstance(notes, chord.Chord):
                                        notes.addLyric(
                                            "chord:" + chordName
                                        )  # NOM DE L'ACCORD EN LYRICS
                                        notes.addLyric("chordid:" + idChord)
                                    else:
                                        notes[0].addLyric("chord:" + chordName)
                                        notes[0].addLyric("chordid:" + idChord)

                                if len(graceXML):
                                    notes[0].duration = duration.Duration(
                                        "eighth"
                                    )
                                    graceNote = notes[0].getGrace()
                                    if graceXML[0].text == "OnBeat":
                                        graceNote.duration.slash = False
                                    voice.insert(offset, graceNote)
                                else:
                                    voice.insert(
                                        offset,
                                        (
                                            notes
                                            if isinstance(notes, chord.Chord)
                                            else notes[0]
                                        ),
                                    )
                                    offset += notes[0].duration.quarterLength
                            else:
                                r = note.Rest()
                                r.duration = self.__getRythmDurationFromIdBeat(
                                    idBeat
                                )
                                if c:
                                    r.addLyric("chord:" + chordName)

                                """"""
                                #
                                if fun != None:
                                    r.addLyric(fun.text)
                                #
                                """"""

                                voice.insert(offset, r)
                                offset += r.duration.quarterLength

    # Get Note of a specified beat (for rythm) from xml according to a given id
    def __getNoteFromId(self, idBeat, idNote):
        # Pitch
        # pitch = self.root.find("./Notes/Note[@id='" + idNote + "']/Properties/Property[@name='ConcertPitch']/Pitch")
        # n = note.Note(self.__getPitchFromXML(pitch))
        note_properties = self.root.find(
            "./Notes/Note[@id='" + idNote + "']/Properties"
        )
        midiPitch = note_properties.find("Property[@name='Midi']/Number").text
        # midiPitch = self.root.find("./Notes/Note[@id='" + idNote + "']/Properties/Property[@name='Midi']/Number").text
        n = note.Note(int(midiPitch))

        ############################################
        ############################################
        slide = note_properties.find("Property[@name='Slide']/Flags")
        ############################################
        ############################################

        mute = note_properties.find("Property[@name='Muted']/Enable")

        release = False
        bendInterval = None
        bendValue = note_properties.findall(
            "Property[@name='BendDestinationValue']/Float"
        )
        additionalSemiTone = 0
        middleValue = note_properties.findall(
            "Property[@name='BendMiddleValue']/Float"
        )
        originValue = note_properties.findall(
            "Property[@name='BendOriginValue']/Float"
        )
        originOffset = note_properties.findall(
            "Property[@name='BendOriginOffset']/Float"
        )
        middleOffset1 = note_properties.findall(
            "Property[@name='BendMiddleOffset1']/Float"
        )
        middleOffset2 = note_properties.findall(
            "Property[@name='BendMiddleOffset2']/Float"
        )
        destinationOffset = note_properties.findall(
            "Property[@name='BendDestinationOffset']/Float"
        )
        if bendValue != []:
            origin = float(originValue[0].text)
            destination = float(bendValue[0].text)
            middle = float(middleValue[0].text)
            originOffset = float(originOffset[0].text)
            destinationOffset = float(destinationOffset[0].text)
            middleOffset1 = float(middleOffset1[0].text)
            middleOffset2 = float(middleOffset2[0].text)
            origin_duration = middleOffset1 - originOffset
            middle_duration = middleOffset2 - middleOffset1
            end_duration = destinationOffset - middleOffset2
            # a note is prebended if it starts higher than 0
            preBend = origin > 0
            if middle > destination:
                # there is a release
                release = True
            if origin == destination:
                if origin == middle:
                    # it is a pre-bend without release
                    additionalSemiTone = origin / 50
                else:
                    # it is a Bend with Release (bend aller-retour)
                    destination = middle
                    additionalSemiTone = abs(destination - origin) / 50
            else:
                additionalSemiTone = abs(destination - origin) / 50
            bendInterval = interval.Interval(additionalSemiTone)

        tie_start = False
        tie_stop = False
        if (
            self.root.findall(
                "./Notes/Note[@id='" + idNote + "']/Tie[@origin='true']"
            )
            != []
        ):
            tie_start = True

        if (
            self.root.findall(
                "./Notes/Note[@id='" + idNote + "']/Tie[@destination='true']"
            )
            != []
        ):
            tie_stop = True

        if tie_start and tie_stop:
            n.tie = tie.Tie("continue")
        elif tie_start:
            n.tie = tie.Tie("start")
        elif tie_stop:
            n.tie = tie.Tie("stop")

        # Add String as an Articulation
        gpif_string_number = int(
            self.root.find(
                "./Notes/Note[@id='"
                + idNote
                + "']/Properties/Property[@name='String']/String"
            ).text
        )
        standard_string_number = (
            -1
        ) * gpif_string_number + 6  # to fit with musicXML/m21 notation (E=6,A=5,...,E=1)
        string = articulations.StringIndication()
        # string.number = self.root.find("./Notes/Note[@id='" + idNote + "']/Properties/Property[@name='String']/String").text
        string.number = str(
            standard_string_number
        )  # take the previous line to come back on GP string notation (E=0, A=1, ...)
        # number should be an int but it might break things
        string.number = int(string.number)

        # Add Fret as an Articulation
        fret = articulations.FretIndication()
        # fret.number = str(int(self.root.find("./Notes/Note[@id='" + idNote + "']/Properties/Property[@name='Fret']/Fret").text) + additionalSemiTone)
        fret.number = int(
            self.root.find(
                "./Notes/Note[@id='"
                + idNote
                + "']/Properties/Property[@name='Fret']/Fret"
            ).text
        )

        # Detect if there is a Hammer-on or a Pull-off
        hopo_start = self.root.find(
            "./Notes/Note[@id='"
            + idNote
            + "']/Properties/Property[@name='HopoOrigin']"
        )
        hopo_end = self.root.find(
            "./Notes/Note[@id='"
            + idNote
            + "']/Properties/Property[@name='HopoDestination']"
        )

        # Add articulations to note
        n.articulations = [string, fret]
        if mute is not None:
            n.articulations.append(articulations.Mute())

        # If a hopo is ended, fill the last hopo
        if hopo_end is not None:
            # This might fail in some specific cases where an hopo is badly
            # annotated in the source file. It should however work fine for hopos
            # between chords (if they are notated correctly)
            if n.string.number == self.hopos[-1][0].string.number:
                self.hopos[-1].append(n)
            elif len(self.hopos) > 1 and len(self.hopos[-2]) == 1:
                if n.string.number == self.hopos[-2][0].string.number:
                    self.hopos[-2].append(n)
            elif len(self.hopos) > 2 and len(self.hopos[-3]) == 1:
                if n.string.number == self.hopos[-3][0].string.number:
                    self.hopos[-3].append(n)
        # If a new hopo begins, add a new hopo
        if hopo_start is not None:
            self.hopos.append([n])

        ################################################
        # TODO : merger le parser de Quentin pour la prise en compte des effets
        # Add Bend as an Articulation
        #
        # #Add PullOff as an Articulation
        # pullOff = articulations.PullOff()
        #
        # hammeron = None
        # Add HammerOn as an Articulation

        # '''
        #         Le travail est un peu sale ici. L'idée est d'ajouter un .number à hammeron pour savoir s'il y en a un.
        # '''

        # hammerOn = articulations.HammerOn()
        # if hammeron == None :
        #     hammeron = self.root.find("./Notes/Note[@id='" + idNote +"']/Properties/Property[@name='HopoOrigin']")
        # if hammeron != None:
        #     #hammerOn.isStart = True
        #     #hammerOn.isEnd = False
        #     hammerOn.number = 1
        # else:
        #     hammerOn.number = 0
        #
        Slide = articulations.IndeterminateSlide()

        ################################################

        # TODO : activer add_technics_to_articulations lorsqu'on sera sûr que ça ne détériore pas les encodings
        # add_technics_to_articulations = False
        #
        # if add_technics_to_articulations:
        #     #if hammerOn.isStart == True:
        #     #    n.articulations.append(hammerOn)
        #     if hammerOn.number == 1:
        #         n.articulations.append(hammerOn)

        # Rythm
        n.duration = self.__getRythmDurationFromIdBeat(idBeat)

        # add Bend
        if bendValue != [] and bendInterval is not None:
            bend = articulations.FretBend()
            bend.bendAlter = bendInterval
            bend.preBend = preBend
            # added attributes for ease of use
            bend.origin_duration = origin_duration
            bend.middle_duration = middle_duration
            bend.end_duration = end_duration
            if release:
                # release is counted as a ratio of the note duration
                bend.release = origin_duration + middle_duration
            n.articulations.append(bend)
        if slide is not None:
            n.articulations.append(Slide)
        n.slideToNext = False
        # if slide != None and int(slide.text) > 2:
        #    n.articulations.append(Slide)
        #    # add a custom attribute that is managed later
        #    n.slideToNext = False
        # elif slide != None and int(slide.text) <= 2:
        #    n.slideToNext = True
        #    self.notes_with_slide_to_next.append(n)
        # else:
        #    n.slideToNext = False

        return n

    # Get Duration type of the rhythm of a specified beat
    def __getRythmDurationFromIdBeat(self, idBeat):
        d = duration.Duration()
        rhythm = self.root.findall("./Beats/Beat[@id='" + idBeat + "']/Rhythm")
        if len(rhythm):
            idRhythm = rhythm[0].get("ref")
            rhythm = self.root.findall(
                "./Rhythms/Rhythm[@id='" + idRhythm + "']"
            )
            if len(rhythm):
                noteValue = rhythm[0].find("NoteValue").text.lower()
                dots = 0
                if rhythm[0].find("AugmentationDot") is not None:
                    dots = rhythm[0].find("AugmentationDot").get("count")
                d.quarterLength = duration.convertTypeToQuarterLength(
                    noteValue, int(dots)
                )
                if rhythm[0].find("PrimaryTuplet") is not None:
                    num = rhythm[0].find("PrimaryTuplet").get("num")
                    den = rhythm[0].find("PrimaryTuplet").get("den")
                    d.appendTuplet(duration.Tuplet(int(num), int(den)))
        return d

    # Return the right representation for a picth (i.e Bb5) from an XML Element :
    # <Pitch>
    #     <Step>B</Step>
    #     <Accidental>b</Accidental>   #Accidental can be NoneType
    #     <Octave>5</Octave>
    # </Pitch>
    def __getPitchFromXML(self, XMLPitch):
        stringPitch = XMLPitch.find("Step").text
        stringPitch += (
            XMLPitch.find("Accidental").text.replace("b", "-")
            if XMLPitch.find("Accidental").text is not None
            else ""
        )
        stringPitch += XMLPitch.find("Octave").text
        return stringPitch

    # Write a stream in a skeleton gp file
    def writeGPFromStream(self, stream):

        return
