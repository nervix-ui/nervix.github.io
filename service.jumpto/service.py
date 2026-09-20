import json
import urllib.request
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

# URL de la base de données JSON mis à jour
JSON_URL = "https://raw.githubusercontent.com/nervix-ui/nervix.github.io/refs/heads/master/intros.json"

ADDON = xbmcaddon.Addon()
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))


class JumpOverlay(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jump_requested = False
        self.is_active = True

    def onInit(self):
        # Donne le focus au bouton dès l'affichage
        self.setFocusId(3001)

    def update_label(self, seconds_left):
        """Met à jour le texte du bouton."""
        if not self.is_active:
            return
        try:
            button = self.getControl(3001)
            button.setLabel(f"Sauter l'intro ({seconds_left}s)")
        except (RuntimeError, AttributeError):
            pass

    def onClick(self, control_id):
        if control_id == 3001:
            self.jump_requested = True
            self.close_window()

    def onAction(self, action):
        # Action 7 = OK / ENTER
        if action.getId() == 7:
            self.jump_requested = True
            self.close_window()
        # Action 92 = RETOUR / ECHAP
        elif action.getId() == 92:
            self.close_window()

    def close_window(self):
        """Ferme la fenêtre proprement et met à jour le statut."""
        self.is_active = False
        self.close()


class JumpToPlayer(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.intros_data = []
        self.load_database()

    def load_database(self):
        """Télécharge la liste des intros depuis GitHub."""
        try:
            req = urllib.request.Request(JSON_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                self.intros_data = json.loads(response.read().decode('utf-8'))
            xbmc.log("[JumpTo] Base de données intros.json chargée avec succès", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"[JumpTo] Erreur lors du chargement du JSON : {e}", xbmc.LOGERROR)

    def onAVStarted(self):
        if not self.isPlayingVideo():
            return

        xbmc.sleep(500)
        info_tag = self.getVideoInfoTag()
        show_title = info_tag.getTVShowTitle()
        season = info_tag.getSeason()
        episode = info_tag.getEpisode()

        if not show_title or season == -1 or episode == -1:
            return

        intro_duration = self.find_intro_duration(show_title, season, episode)
        if intro_duration:
            self.show_overlay(intro_duration)

    def find_intro_duration(self, show, season, episode):
        """Recherche la durée de l'intro dans les données JSON."""
        for item in self.intros_data:
            if item.get("show").lower() != show.lower() or item.get("season") != season:
                continue

            ep_data = item.get("episode")
            if isinstance(ep_data, int) and ep_data == episode:
                return item.get("intro_length")
            if isinstance(ep_data, list) and episode in ep_data:
                return item.get("intro_length")
            if isinstance(ep_data, str) and "-" in ep_data:
                try:
                    start, end = map(int, ep_data.split("-"))
                    if start <= episode <= end:
                        return item.get("intro_length")
                except ValueError:
                    pass
        return None

    def show_overlay(self, duration):
        """Affiche le bouton overlay pendant 10 secondes."""
        overlay = JumpOverlay(
            "overlay_jumpto.xml",
            ADDON_PATH,
            "Default",
            "1080i"
        )
        overlay.show()

        monitor = xbmc.Monitor()
        time_limit = 10  # Durée d'affichage en secondes

        for remaining in range(time_limit, 0, -1):
            if overlay.jump_requested or monitor.abortRequested() or not overlay.is_active:
                break

            overlay.update_label(remaining)

            # Pause de 1 seconde découpée pour intercepter le clic sans délai
            for _ in range(10):
                if overlay.jump_requested or monitor.abortRequested() or not overlay.is_active:
                    break
                xbmc.sleep(100)

        # Effectue le saut si demandé
        if overlay.jump_requested:
            self.seekTime(duration)

        if overlay.is_active:
            overlay.close_window()
        del overlay


if __name__ == '__main__':
    player = JumpToPlayer()
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break