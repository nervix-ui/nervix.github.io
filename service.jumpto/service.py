
import json
import urllib.request
import xbmc
import xbmcgui

JSON_URL = "https://raw.githubusercontent.com/nervix-ui/nervix.github.io/refs/heads/master/intros.json"
ADDON_ID = "service.jumpto"

class JumpOverlay(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jump_requested = False

    def onInit(self):
        # Donne le focus au bouton dès l'affichage
        self.setFocusId(3001)

    def onClick(self, control_id):
        if control_id == 3001:
            self.jump_requested = True
            self.close()

    def Action(self, action):
        # 7 = Touche SELECT / ENTER de la télécommande ou du clavier
        if action.getId() == 7:
            self.jump_requested = True
            self.close()
        # 92 = Touche BACK / ESCAPE
        elif action.getId() == 92:
            self.close()


class JumpToPlayer(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.intros_data = []
        self.load_database()

    def load_database(self):
        """Charge la base de données JSON."""
        try:
            req = urllib.request.Request(JSON_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                self.intros_data = json.loads(response.read().decode('utf-8'))
            xbmc.log(f"[JumpTo] JSON chargé avec succès avec {len(self.intros_data)} entrées", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"[JumpTo] Erreur chargement JSON : {e}", xbmc.LOGERROR)

    def onAVStarted(self):
        """Déclenché dès que l'audio/vidéo commence."""
        if not self.isPlayingVideo():
            return

        # Attente très courte pour s'assurer que les métadonnées de la vidéo sont chargées
        xbmc.sleep(500)
        info_tag = self.getVideoInfoTag()
        show_title = info_tag.getTVShowTitle()
        season = info_tag.getSeason()
        episode = info_tag.getEpisode()

        xbmc.log(f"[JumpTo] Lecture détectée : {show_title} S{season}E{episode}", xbmc.LOGINFO)

        if not show_title or season == -1 or episode == -1:
            return

        intro_duration = self.find_intro_duration(show_title, season, episode)
        if intro_duration:
            xbmc.log(f"[JumpTo] Intro trouvée : {intro_duration}s", xbmc.LOGINFO)
            self.prompt_jump(intro_duration)

    def find_intro_duration(self, show, season, episode):
        """Vérifie si l'épisode correspond à une entrée du JSON."""
        for item in self.intros_data:
            if item.get("show").lower() != show.lower() or item.get("season") != season:
                continue

            ep_data = item.get("episode")

            # Cas 1 : Nombre unique (ex: 1)
            if isinstance(ep_data, int) and ep_data == episode:
                return item.get("intro_length")

            # Cas 2 : Liste d'épisodes (ex: [1, 2, 3])
            if isinstance(ep_data, list) and episode in ep_data:
                return item.get("intro_length")

            # Cas 3 : Intervalle sous forme de chaîne (ex: "1-13")
            if isinstance(ep_data, str) and "-" in ep_data:
                try:
                    start, end = map(int, ep_data.split("-"))
                    if start <= episode <= end:
                        return item.get("intro_length")
                except ValueError:
                    pass
        return None

    def show_overlay(self, duration):
        # Instanciation du dialogue XML
        overlay = JumpOverlay(
            "overlay_jumpto.xml",
            xbmc.addDirectoryURL(ADDON_ID),
            "Default",
            "1080i"
        )
        
        # Affichage non-bloquant
        overlay.show()

        # Attendre 10 secondes max ou que l'utilisateur clique
        monitor = xbmc.Monitor()
        count = 0
        while count < 100 and not monitor.abortRequested() and overlay.isCreated():
            if overlay.jump_requested:
                current_time = self.getTime()
                self.seekTime(current_time + duration)
                break
            xbmc.sleep(100)  # Boucle de 100ms
            count += 1

        # Fermeture propre du bouton s'il est encore ouvert
        if overlay.isCreated():
            overlay.close()
        del overlay


if __name__ == '__main__':
    player = JumpToPlayer()
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break