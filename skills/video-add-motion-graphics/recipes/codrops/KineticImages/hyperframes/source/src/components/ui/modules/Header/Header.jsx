import styles from './Header.module.scss';

function Header({ children }) {
    return (
        <div className={styles.header}>
            <div className={styles.wrapper}>{children}</div>
        </div>
    );
}

export default Header;
